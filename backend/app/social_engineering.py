"""
Rule-based social engineering detector — no LLM required.

Three analysis components:
  1. Urgency manipulation — phrases that create panic or artificial time pressure
  2. Credential harvesting — explicit requests for passwords, PINs, bank/card details
  3. Trust score 0–100 — composite deduction model aggregating all risk signals
"""
import re
from dataclasses import dataclass, field

# ── Urgency manipulation patterns ─────────────────────────────────────────────
# Grouped by psychological tactic; each entry is a case-insensitive regex.

_RAW_URGENCY: dict[str, list[str]] = {
    # Direct threats to suspend/close/delete the account
    "account_threat": [
        r"account.{0,25}(suspend|terminat|clos|disabl|block|lock|delet)",
        r"(suspend|terminat|clos|disabl|block|lock|delet).{0,25}account",
        r"lose.{0,20}access",
        r"access.{0,20}(removed?|revoked?|terminated?|blocked?)",
    ],
    # Fake security alerts to induce panic
    "security_alarm": [
        r"(unauthori[sz]ed|suspicious).{0,25}(access|activit|log.?in|attempt|sign.?in)",
        r"account.{0,20}(compromised?|hacked?|breached?|at risk)",
        r"(compromised?|hacked?|breached?).{0,20}account",
        r"security.{0,15}(alert|breach|incident|warning|notice|compromis)",
        r"detected.{0,25}(suspicious|unusual|unauthori[sz]ed)",
    ],
    # Artificial deadline / countdown pressure
    "time_pressure": [
        r"within.{0,12}(24|48|72)\s*hours?",
        r"(expires?|expir(?:ing|ation)).{0,25}(today|soon|immediately|now|midnight)",
        r"(today|tonight|immediately|right now|by end of day|by midnight).{0,20}(or|else|otherwise)",
        r"(final|last)\s+(notice|warning|chance|reminder|call)",
        r"(act|respond|click|verify|confirm|update).{0,20}(now|immediately|today|urgently|right away)",
        r"(limited|running out of).{0,15}time",
        r"deadline.{0,15}(today|tomorrow|passed|imminent|tonight)",
        r"\btime.sensitive\b",
        r"(don.t|do not).{0,12}(delay|ignore|miss).{0,20}(this|it)",
    ],
    # Fear of losing something valuable
    "loss_aversion": [
        r"(miss|lose|forfeit).{0,25}(opportunity|offer|reward|prize|benefit|access|funds?)",
        r"(offer|deal|discount|promo(?:tion)?).{0,20}(expires?|ends?|runs? out)",
        r"(unclaim|uncollect).{0,20}(reward|prize|funds?|money|package|parcel|cash)",
        r"pending.{0,15}(reward|payment|delivery|package|parcel|transfer|refund)",
    ],
    # Authority impersonation + legal threats
    "authority_threat": [
        r"(legal|law.enforcement|irs|fbi|police|court|government).{0,25}(action|proceed|warrant|summons|penalty|fine|case)",
        r"(arrest|prosecut|jail|prison|detain).{0,20}(if|unless|without|will)",
        r"failure.{0,25}(comply|respond|confirm|verify).{0,20}(result|lead|cause|subject)",
        r"(must|required|mandated?|obligated?).{0,25}(verify|confirm|update|respond|act).{0,15}(immediately|now|today|or)",
        r"(warrant|subpoena|lawsuit|legal action).{0,20}(issued?|filed?|initiat|pending)",
    ],
}

# ── Credential harvesting patterns ────────────────────────────────────────────

_RAW_CREDENTIALS: dict[str, list[str]] = {
    "password": [
        r"\bpassword\b.{0,50}(enter|provid|submit|type|confirm|reset|update|send|share|click|verif)",
        r"(enter|provid|submit|type|confirm|reset|update|send|share|click|verif).{0,50}\bpassword\b",
        r"(current|old|new|your)\s+password",
        r"re.?enter.{0,15}password",
    ],
    "pin": [
        r"\bpin\b.{0,25}(enter|provid|submit|type|confirm|verif|send)",
        r"(enter|provid|submit|type|verif|send).{0,25}\bpin\b",
        r"[46].?digit.{0,15}(code|pin|number)",
        r"personal\s+identification\s+number",
    ],
    "ssn": [
        r"social.?security.{0,15}(number|no\.?|#|id|num)?",
        r"\bssn\b",
        r"\bsin\b.{0,15}(number|verif|provid|enter|card)",
        r"9.?digit.{0,15}(number|id|identif)",
    ],
    "bank_account": [
        r"(bank.?account|account.?number|routing.?number|sort.?code|iban|swift.?code)",
        r"(checking|savings).{0,15}account.{0,25}(number|detail|info)",
        r"wire.{0,15}(transfer|detail|info|instruction)",
        r"direct.?debit.{0,25}(detail|info|number|set.?up|authoris|authoriz)",
        r"(remittance|ach|bacs).{0,20}(detail|info|number|instruction)",
    ],
    "card_details": [
        r"(credit|debit).{0,15}card.{0,25}(number|detail|info|no\.?|#)",
        r"\bcvv\b|\bcvc\b|\bcvv2\b|\bcvc2\b",
        r"card.?verif.{0,25}(value|number|code)",
        r"expir.{0,25}(date|month|year).{0,15}card",
        r"(enter|provid|submit|type|verif|confirm).{0,40}(card|payment).{0,25}(detail|info|number)",
        r"16.?digit.{0,15}(card|number)",
    ],
    "identity": [
        r"(date of birth|d\.?o\.?b\.?).{0,25}(enter|provid|submit|verif|confirm)",
        r"mother.?s?\s+maiden.{0,15}name",
        r"(birth.?place|place\s+of\s+birth)",
        r"(national\s+id|passport\s+(number|no\.?)|driver.?s?\s+licen)",
        r"(tax\s+(id|identification)|tin\b|ein\b).{0,20}(number|provid|enter|verif)",
    ],
}

# ── Compile patterns ──────────────────────────────────────────────────────────

_URGENCY_COMPILED: dict[str, list[re.Pattern]] = {
    cat: [re.compile(p, re.IGNORECASE) for p in pats]
    for cat, pats in _RAW_URGENCY.items()
}

_CREDENTIAL_COMPILED: dict[str, list[re.Pattern]] = {
    cat: [re.compile(p, re.IGNORECASE) for p in pats]
    for cat, pats in _RAW_CREDENTIALS.items()
}

# ── Risk weights ──────────────────────────────────────────────────────────────

_URGENCY_WEIGHTS: dict[str, int] = {
    "account_threat":   12,
    "security_alarm":   10,
    "time_pressure":     8,
    "loss_aversion":     6,
    "authority_threat": 15,
}
_MAX_URGENCY_DEDUCTION = 35

_CREDENTIAL_WEIGHTS: dict[str, int] = {
    "password":     22,
    "pin":          20,
    "ssn":          25,
    "bank_account": 25,
    "card_details": 25,
    "identity":     18,
}
_MAX_CREDENTIAL_DEDUCTION = 40

_LINK_FLAG_WEIGHTS: dict[str, int] = {
    "raw_ip_address":     18,
    "domain_mismatch":    15,
    "brand_mismatch":     12,
    "redirect_parameter": 10,
    "shortened_url":       5,
}
_MAX_LINK_DEDUCTION = 30

# Extra deduction when urgency pressure and credential harvesting co-occur
_SYNERGY_PENALTY = 10


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class UrgencyHit:
    category: str
    matched_text: str   # the substring that triggered the match


@dataclass
class CredentialHit:
    category: str
    matched_text: str


@dataclass
class TrustReport:
    trust_score: int                      # 0 (malicious) – 100 (trusted)
    risk_level: str                       # "low" | "moderate" | "high" | "critical"
    urgency_hits: list[UrgencyHit]        # all urgency matches (ordered, deduplicated text)
    urgency_categories: list[str]         # unique categories found
    credential_hits: list[CredentialHit]  # all credential matches
    credential_categories: list[str]      # unique categories found
    link_flags: list[str]                 # passed through from link_analyzer
    score_breakdown: dict[str, int]       # per-component deductions for UI display
    summary: str


# ── Detection functions ───────────────────────────────────────────────────────

def _search_all(text: str, compiled: dict[str, list[re.Pattern]]) -> dict[str, list[str]]:
    """Return {category: [matched_text, ...]} for every pattern that fires."""
    seen_spans: set[tuple[int, int]] = set()
    hits: dict[str, list[str]] = {}

    for cat, patterns in compiled.items():
        cat_hits: list[str] = []
        for pat in patterns:
            for m in pat.finditer(text):
                span = (m.start(), m.end())
                if span not in seen_spans:
                    seen_spans.add(span)
                    # Truncate match for display; strip surrounding whitespace
                    snip = text[m.start():m.end()].strip()[:120]
                    cat_hits.append(snip)
        if cat_hits:
            hits[cat] = cat_hits

    return hits


def detect_urgency(text: str) -> list[UrgencyHit]:
    """Return all urgency-manipulation matches found in text."""
    raw = _search_all(text, _URGENCY_COMPILED)
    hits: list[UrgencyHit] = []
    for cat, snippets in raw.items():
        for snip in snippets:
            hits.append(UrgencyHit(category=cat, matched_text=snip))
    return hits


def detect_credential_requests(text: str) -> list[CredentialHit]:
    """Return all credential-harvesting matches found in text."""
    raw = _search_all(text, _CREDENTIAL_COMPILED)
    hits: list[CredentialHit] = []
    for cat, snippets in raw.items():
        for snip in snippets:
            hits.append(CredentialHit(category=cat, matched_text=snip))
    return hits


# ── Trust score ───────────────────────────────────────────────────────────────

def _risk_level(score: int) -> str:
    if score >= 80:
        return "low"
    if score >= 60:
        return "moderate"
    if score >= 40:
        return "high"
    return "critical"


def _build_summary(
    trust_score: int,
    risk_level: str,
    urgency_cats: list[str],
    credential_cats: list[str],
    link_flags: list[str],
) -> str:
    parts: list[str] = []

    if urgency_cats:
        readable = {
            "account_threat":   "account-closure threats",
            "security_alarm":   "fake security alarms",
            "time_pressure":    "artificial time pressure",
            "loss_aversion":    "loss-aversion manipulation",
            "authority_threat": "legal/authority threats",
        }
        labels = [readable.get(c, c) for c in urgency_cats]
        parts.append(f"Urgency tactics detected: {', '.join(labels)}.")

    if credential_cats:
        readable = {
            "password":     "password",
            "pin":          "PIN",
            "ssn":          "SSN/national ID",
            "bank_account": "bank account details",
            "card_details": "card details",
            "identity":     "identity documents",
        }
        labels = [readable.get(c, c) for c in credential_cats]
        parts.append(f"Sensitive data requested: {', '.join(labels)}.")

    if link_flags:
        parts.append(f"Suspicious link patterns: {', '.join(link_flags)}.")

    if not parts:
        return f"Trust score {trust_score}/100 — no social engineering signals detected."

    return (
        f"Trust score {trust_score}/100 ({risk_level} risk). "
        + " ".join(parts)
    )


def compute_trust_score(
    urgency_hits: list[UrgencyHit],
    credential_hits: list[CredentialHit],
    link_flags: list[str],
) -> TrustReport:
    """Aggregate all signals into a single 0–100 trust score."""

    # Unique categories hit
    urgency_cats = sorted({h.category for h in urgency_hits})
    credential_cats = sorted({h.category for h in credential_hits})

    # Urgency deduction
    urgency_raw = sum(_URGENCY_WEIGHTS.get(c, 5) for c in urgency_cats)
    urgency_ded = min(urgency_raw, _MAX_URGENCY_DEDUCTION)

    # Credential deduction
    cred_raw = sum(_CREDENTIAL_WEIGHTS.get(c, 10) for c in credential_cats)
    cred_ded = min(cred_raw, _MAX_CREDENTIAL_DEDUCTION)

    # Link deduction
    link_raw = sum(_LINK_FLAG_WEIGHTS.get(f, 5) for f in link_flags)
    link_ded = min(link_raw, _MAX_LINK_DEDUCTION)

    # Synergy penalty — urgency + credentials together is a classic phishing combo
    synergy = _SYNERGY_PENALTY if urgency_ded > 0 and cred_ded > 0 else 0

    trust_score = max(0, 100 - urgency_ded - cred_ded - link_ded - synergy)
    risk_level = _risk_level(trust_score)

    breakdown = {
        "urgency_deduction":    urgency_ded,
        "credential_deduction": cred_ded,
        "link_deduction":       link_ded,
        "synergy_penalty":      synergy,
    }

    return TrustReport(
        trust_score=trust_score,
        risk_level=risk_level,
        urgency_hits=urgency_hits,
        urgency_categories=urgency_cats,
        credential_hits=credential_hits,
        credential_categories=credential_cats,
        link_flags=sorted(set(link_flags)),
        score_breakdown=breakdown,
        summary=_build_summary(trust_score, risk_level, urgency_cats, credential_cats, link_flags),
    )


# ── Public convenience function ───────────────────────────────────────────────

def analyze_trust(
    subject: str,
    body: str,
    link_flags: list[str] | None = None,
) -> TrustReport:
    """
    Full trust analysis on an email.

    Pass pre-computed link_flags from link_analyzer.analyze_email_links() to
    avoid redundant link extraction; omit to skip link scoring.
    """
    text = f"{subject}\n{body}" if subject else body
    urgency_hits = detect_urgency(text)
    credential_hits = detect_credential_requests(text)
    return compute_trust_score(
        urgency_hits,
        credential_hits,
        link_flags or [],
    )
