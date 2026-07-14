"""
Flowchart extraction agent.

Public API
----------
detect_flowchart(subject, body) -> dict
  Returns a FlowchartResponse-compatible dict.
  has_flowchart=False when no plan/process structure is detected.

The agent also generates ready-to-render Mermaid flowchart syntax from the
extracted nodes and edges, so the frontend does not need a graph-layout engine.
"""
from app.chains.flowchart_chain import MAX_INPUT_CHARS, get_flowchart_chain

__all__ = ["detect_flowchart"]

_VALID_NODE_TYPES = frozenset({"start", "end", "step", "decision"})
_VALID_CHART_TYPES = frozenset({"sequential", "branching", "parallel"})

_FALLBACK: dict = {
    "has_flowchart":   False,
    "title":           "",
    "flowchart_type":  None,
    "nodes":           [],
    "edges":           [],
    "mermaid":         "",
}


# ── Coercion helpers ──────────────────────────────────────────────────────────

def _str(val, default: str = "") -> str:
    return str(val).strip() if val is not None else default


def _coerce_node(raw: dict, seen_ids: set) -> dict | None:
    nid   = _str(raw.get("id"))
    label = _str(raw.get("label"))
    if not nid or not label or nid in seen_ids:
        return None
    seen_ids.add(nid)
    ntype = _str(raw.get("type", "step"))
    if ntype not in _VALID_NODE_TYPES:
        ntype = "step"
    return {
        "id":          nid,
        "label":       label,
        "type":        ntype,
        "description": _str(raw.get("description")),
    }


def _coerce_edge(raw: dict, valid_ids: set) -> dict | None:
    source = _str(raw.get("source"))
    target = _str(raw.get("target"))
    if not source or not target:
        return None
    if source not in valid_ids or target not in valid_ids:
        return None
    return {
        "source": source,
        "target": target,
        "label":  _str(raw.get("label")),
    }


# ── Mermaid generation ────────────────────────────────────────────────────────

def _mermaid_node_line(node: dict) -> str:
    nid   = node["id"]
    label = node["label"]
    desc  = node["description"]
    text  = f"{label}\\n{desc}" if desc else label

    ntype = node["type"]
    if ntype in ("start", "end"):
        return f'  {nid}(["{text}"])'
    if ntype == "decision":
        return f'  {nid}{{"{text}"}}'
    return f'  {nid}["{text}"]'


def _to_mermaid(nodes: list[dict], edges: list[dict]) -> str:
    if not nodes:
        return ""
    lines = ["flowchart TD"]
    for node in nodes:
        lines.append(_mermaid_node_line(node))
    for edge in edges:
        src, tgt, lbl = edge["source"], edge["target"], edge["label"]
        if lbl:
            lines.append(f"  {src} -->|\"{lbl}\"| {tgt}")
        else:
            lines.append(f"  {src} --> {tgt}")
    return "\n".join(lines)


# ── Public function ───────────────────────────────────────────────────────────

async def detect_flowchart(subject: str, body: str) -> dict:
    combined = f"Subject: {subject}\n\n{body}" if subject else body
    email_text = combined[:MAX_INPUT_CHARS]

    try:
        raw: dict = await get_flowchart_chain().ainvoke({"email_text": email_text})
    except Exception as exc:
        return {**_FALLBACK, "error": str(exc)}

    if not raw.get("has_flowchart"):
        return _FALLBACK

    seen_ids: set[str] = set()
    nodes = [
        n for item in (raw.get("nodes") or [])
        if (n := _coerce_node(item, seen_ids)) is not None
    ]

    if len(nodes) < 3:
        return _FALLBACK

    valid_ids = {n["id"] for n in nodes}
    edges = [
        e for item in (raw.get("edges") or [])
        if (e := _coerce_edge(item, valid_ids)) is not None
    ]

    chart_type = _str(raw.get("flowchart_type"))
    if chart_type not in _VALID_CHART_TYPES:
        chart_type = "sequential"

    return {
        "has_flowchart":  True,
        "title":          _str(raw.get("title")),
        "flowchart_type": chart_type,
        "nodes":          nodes,
        "edges":          edges,
        "mermaid":        _to_mermaid(nodes, edges),
    }
