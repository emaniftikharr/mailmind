"""
Rule-based link extractor and risk analyzer — no LLM required.

Three checks per link:
  1. Shortened URL   — href domain is in a known URL-shortener list
  2. Domain mismatch — display text contains a URL whose domain differs from href domain
  3. Brand mismatch  — display text mentions a brand whose official domain differs from href
  4. Raw IP address  — href uses a numeric IP instead of a hostname
  5. Redirect param  — href contains a ?url=, ?redirect=, or similar open-redirect parameter
"""
import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

# ── Constants ─────────────────────────────────────────────────────────────────

# Known URL shortener domains (canonical form, no www.)
SHORTENER_DOMAINS: frozenset[str] = frozenset({
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "buff.ly",
    "short.link", "is.gd", "rb.gy", "cutt.ly", "tiny.cc", "shorte.st",
    "adf.ly", "lnkd.in", "dlvr.it", "su.pr", "cli.gs", "snip.ly",
    "bc.vc", "po.st", "fur.ly", "linktr.ee", "smarturl.it", "yourls.org",
    "qr.ae", "ift.tt", "x.co", "v.gd", "mcaf.ee", "2.ly", "flic.kr",
})

# Brand keyword → set of legitimate apex domains
BRAND_DOMAINS: dict[str, frozenset[str]] = {
    "paypal":        frozenset({"paypal.com", "paypal.me"}),
    "amazon":        frozenset({"amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
                                 "aws.amazon.com", "amazon.ca"}),
    "apple":         frozenset({"apple.com", "icloud.com"}),
    "microsoft":     frozenset({"microsoft.com", "office.com", "live.com",
                                 "outlook.com", "hotmail.com", "azure.com"}),
    "google":        frozenset({"google.com", "gmail.com", "accounts.google.com",
                                 "drive.google.com", "workspace.google.com"}),
    "facebook":      frozenset({"facebook.com", "fb.com", "meta.com"}),
    "instagram":     frozenset({"instagram.com"}),
    "netflix":       frozenset({"netflix.com"}),
    "stripe":        frozenset({"stripe.com", "dashboard.stripe.com"}),
    "bank of america": frozenset({"bankofamerica.com"}),
    "chase":         frozenset({"chase.com", "jpmorgan.com"}),
    "wells fargo":   frozenset({"wellsfargo.com"}),
    "irs":           frozenset({"irs.gov"}),
    "fedex":         frozenset({"fedex.com"}),
    "ups":           frozenset({"ups.com"}),
    "dhl":           frozenset({"dhl.com"}),
    "linkedin":      frozenset({"linkedin.com", "lnkd.in"}),
    "twitter":       frozenset({"twitter.com", "x.com", "t.co"}),
    "dropbox":       frozenset({"dropbox.com", "db.tt"}),
    "github":        frozenset({"github.com", "gist.github.com"}),
}

# Query parameter names used in open-redirect attacks
_REDIRECT_PARAMS: frozenset[str] = frozenset({
    "url", "redirect", "redirect_url", "return", "return_url",
    "next", "goto", "target", "link", "continue", "dest", "destination",
})

# Risk flag identifiers
FLAG_SHORTENED        = "shortened_url"
FLAG_DOMAIN_MISMATCH  = "domain_mismatch"
FLAG_BRAND_MISMATCH   = "brand_mismatch"
FLAG_RAW_IP           = "raw_ip_address"
FLAG_REDIRECT_PARAM   = "redirect_parameter"

# Regex: matches http(s) URLs in plain text; grabs URL up to whitespace/closing punct
_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)

# Regex: IPv4 address (for domain-field check)
_IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

# ── HTML link parser ──────────────────────────────────────────────────────────

class _HrefParser(HTMLParser):
    """Collect (href, display_text) pairs from <a> tags."""

    def __init__(self) -> None:
        super().__init__()
        self._pairs: list[tuple[str, str]] = []
        self._href: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            for name, val in attrs:
                if name == "href" and val and val.lower().startswith("http"):
                    self._href = val
                    self._buf = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            self._pairs.append((self._href, "".join(self._buf).strip()))
            self._href = None
            self._buf = []

    @property
    def pairs(self) -> list[tuple[str, str]]:
        return self._pairs

# ── Per-link helpers ──────────────────────────────────────────────────────────

def _apex_domain(url: str) -> str:
    """Return the apex domain (no www., no port) of a URL, or '' on error."""
    try:
        host = urlparse(url).netloc.lower()
        host = host.split(":")[0]          # strip port
        host = host.removeprefix("www.")
        return host
    except Exception:
        return ""


def _url_in_text(text: str) -> str:
    """Return the first HTTP URL embedded in display text, or ''."""
    m = _URL_RE.search(text)
    return m.group(0) if m else ""


def _brand_mismatch(display_text: str, href_domain: str) -> str:
    """
    Return the brand name if display text mentions a known brand but the href
    domain is not one of that brand's official domains; else return ''.
    """
    low = display_text.lower()
    for brand, official in BRAND_DOMAINS.items():
        if brand in low:
            match = any(
                href_domain == d or href_domain.endswith("." + d)
                for d in official
            )
            if not match:
                return brand
    return ""


def _redirect_param(url: str) -> bool:
    try:
        params = set(parse_qs(urlparse(url).query).keys())
        return bool(params & _REDIRECT_PARAMS)
    except Exception:
        return False

# ── Public API ────────────────────────────────────────────────────────────────

@dataclass
class LinkInfo:
    url: str
    display_text: str
    domain: str
    display_domain: str           # domain found inside display text URL, if any
    is_shortened: bool
    risk_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "url":          self.url,
            "display_text": self.display_text,
            "domain":       self.domain,
            "display_domain": self.display_domain,
            "is_shortened": self.is_shortened,
            "risk_flags":   self.risk_flags,
        }


def analyze_link(url: str, display_text: str) -> LinkInfo:
    """Run all risk checks on a single (url, display_text) pair."""
    domain = _apex_domain(url)
    flags: list[str] = []
    display_domain = ""

    # 1. Shortened URL
    if domain in SHORTENER_DOMAINS:
        flags.append(FLAG_SHORTENED)

    # 2. Raw IP address
    if _IPV4_RE.match(domain.split(":")[0]):
        flags.append(FLAG_RAW_IP)

    # 3. Open-redirect parameter
    if _redirect_param(url):
        flags.append(FLAG_REDIRECT_PARAM)

    # 4. Domain mismatch — display text contains a URL with a different domain
    embedded = _url_in_text(display_text)
    if embedded and embedded.lower().rstrip("/") != url.lower().rstrip("/"):
        display_domain = _apex_domain(embedded)
        if display_domain and display_domain != domain:
            flags.append(FLAG_DOMAIN_MISMATCH)

    # 5. Brand mismatch — display text names a brand not matching the href domain
    brand = _brand_mismatch(display_text, domain)
    if brand:
        flags.append(FLAG_BRAND_MISMATCH)

    return LinkInfo(
        url=url,
        display_text=display_text,
        domain=domain,
        display_domain=display_domain,
        is_shortened=FLAG_SHORTENED in flags,
        risk_flags=flags,
    )


def extract_links(body: str, is_html: bool = False) -> list[tuple[str, str]]:
    """
    Return (url, display_text) pairs from the email body.

    HTML mode: parses <a href> tags first, then collects bare URLs not already
    captured.  Plain-text mode: regex-only, display_text == url.
    """
    pairs: list[tuple[str, str]] = []

    if is_html:
        parser = _HrefParser()
        parser.feed(body)
        pairs.extend(parser.pairs)

        # Also find bare URLs in the stripped text
        stripped = html.unescape(re.sub(r"<[^>]+>", " ", body))
        href_set = {url for url, _ in pairs}
        for m in _URL_RE.finditer(stripped):
            url = m.group(0).rstrip(".,;:!?\"'")
            if url not in href_set:
                pairs.append((url, url))
                href_set.add(url)
    else:
        seen: set[str] = set()
        for m in _URL_RE.finditer(body):
            url = m.group(0).rstrip(".,;:!?\"'")
            if url not in seen:
                pairs.append((url, url))
                seen.add(url)

    return pairs


def analyze_email_links(
    body: str,
    subject: str = "",
    is_html: bool = False,
) -> dict:
    """
    Full link analysis for an email.

    Combines subject + body for extraction (phishing links sometimes appear in
    subject lines). Returns a structured report suitable for the /links endpoint
    and as enriched context for the phishing agent.
    """
    text = f"{subject}\n{body}" if subject else body
    pairs = extract_links(text, is_html=is_html)

    # Deduplicate by URL while preserving order
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for url, display in pairs:
        if url not in seen:
            seen.add(url)
            unique.append((url, display))

    results = [analyze_link(url, display) for url, display in unique]
    flagged = [r for r in results if r.risk_flags]

    all_flags: set[str] = set()
    for r in flagged:
        all_flags.update(r.risk_flags)

    return {
        "links":      [r.to_dict() for r in results],
        "total":      len(results),
        "flagged":    len(flagged),
        "risk_flags": sorted(all_flags),
    }
