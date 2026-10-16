"""Bounded public search: free You.com first, Tavily only when requested as critical."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit
from cloud.public_search import YouSearchMCP

ROOT = Path(__file__).resolve().parents[1]
TAVILY_ENDPOINT = "https://api.tavily.com/search"
YOU_ENDPOINT = "https://api.you.com/mcp?profile=free"
ENDPOINT = TAVILY_ENDPOINT  # Backward-compatible name used by existing checks.
MAX_RESPONSE_BYTES = 131072


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _setting(name):
    value = os.environ.get(name)
    if value is not None:
        return value
    try:
        lines = (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == name:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            return value
    return None


class TavilySearch:
    """Return bounded search-result snippets and URLs, never Tavily's generated answer."""

    def __init__(self, api_key, opener=None, clock=None):
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("Tavily research key is missing.")
        self.api_key = api_key.strip()
        self.opener = opener or urllib.request.build_opener(NoRedirect())
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def __call__(self, query, *, max_sources, max_bytes, timeout):
        if not isinstance(query, str) or not query.strip() or len(query) > 2000:
            raise ValueError("Research query is invalid.")
        if type(max_sources) is not int or not 1 <= max_sources <= 6:
            raise ValueError("Research source limit is invalid.")
        if type(max_bytes) is not int or not 512 <= max_bytes <= 8000:
            raise ValueError("Research byte limit is invalid.")
        if not isinstance(timeout, (int, float)) or not 1 <= timeout <= 8:
            raise ValueError("Research timeout is invalid.")

        body = json.dumps({
            "query": query.strip(),
            "search_depth": "basic",
            "chunks_per_source": 1,
            "max_results": max_sources,
            "topic": "general",
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "auto_parameters": False,
            "include_usage": True,
            "safe_search": True,
        }, separators=(",", ":")).encode()
        request = urllib.request.Request(
            TAVILY_ENDPOINT, data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self.api_key},
        )
        try:
            with self.opener.open(request, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except (OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
            raise ValueError("Public research provider is unavailable.") from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Public research response is too large.")
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Public research returned invalid data.") from exc

        stamp = self.clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        results = payload.get("results", [])
        records, seen = [], set()
        for item in results if isinstance(results, list) else []:
            if not isinstance(item, dict):
                continue
            url, content = item.get("url"), item.get("content")
            if not isinstance(url, str) or not isinstance(content, str):
                continue
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                continue
            url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
            excerpt = " ".join(content.split())[:2000]
            if url in seen or not excerpt:
                continue
            record = {
                "id": f"source-{len(records) + 1}",
                "url": url,
                "retrieved_at": stamp,
                "claim": excerpt[:300],
                "excerpt": excerpt,
            }
            from brain.verification import evidence_block
            try:
                evidence_block(records + [record])
            except ValueError:
                continue
            encoded = json.dumps(records + [record], ensure_ascii=False,
                                 separators=(",", ":")).encode()
            if len(encoded) > max_bytes:
                continue
            records.append(record)
            seen.add(url)
            if len(records) >= max_sources:
                break
        if not records:
            raise ValueError("Public research returned no usable HTTPS sources.")
        return records


class HybridSearch:
    """Use the free provider normally; spend a Tavily credit only for an explicit critical query."""

    CRITICAL_PREFIXES = ("critical research:", "important research:")

    def __init__(self, free_search, critical_search=None, monotonic=None):
        self.free_search = free_search
        self.critical_search = critical_search
        self.monotonic = monotonic or time.monotonic

    def __call__(self, query, *, max_sources, max_bytes, timeout):
        stripped = query.strip()
        prefix = next((value for value in self.CRITICAL_PREFIXES
                       if stripped.lower().startswith(value)), None)
        if not prefix or self.critical_search is None:
            return self.free_search(stripped, max_sources=max_sources,
                                    max_bytes=max_bytes, timeout=timeout)

        clean_query = stripped[len(prefix):].strip()
        if not clean_query:
            raise ValueError("Research query is invalid.")
        started = self.monotonic()
        first_limit = max(1, max_sources // 2)
        records = self.critical_search(clean_query, max_sources=first_limit,
                                       max_bytes=max_bytes, timeout=max(1, timeout / 2))
        remaining = timeout - (self.monotonic() - started)
        if remaining < 1 or len(records) >= max_sources:
            return records
        try:
            free_records = self.free_search(
                clean_query, max_sources=max_sources - len(records),
                max_bytes=max_bytes, timeout=remaining)
        except ValueError:
            return records
        seen = {record["url"] for record in records}
        for record in free_records:
            if record["url"] in seen:
                continue
            candidate = dict(record, id=f"source-{len(records) + 1}")
            encoded = json.dumps(records + [candidate], ensure_ascii=False,
                                 separators=(",", ":")).encode()
            if len(encoded) <= max_bytes:
                records.append(candidate)
                seen.add(candidate["url"])
            if len(records) >= max_sources:
                break
        return records


def _configured_search():
    """Prefer keyless search; reserve Tavily for explicit critical-research prompts."""
    free_search = YouSearchMCP() if _setting("LYA_FREE_RESEARCH_ENABLED") == "1" else None
    tavily = None
    if (_setting("LYA_TAVILY_RESEARCH_ENABLED") == "1" and
            _setting("LYA_TAVILY_FREE_ONLY") == "1"):
        key = _setting("TAVILY_API_KEY")
        tavily = TavilySearch(key) if key else None
    if free_search:
        return HybridSearch(free_search, tavily)
    return tavily



def default_researcher():
    """Preserve explicit provider opt-ins; add page research and local attempt quota."""
    from cloud.web_research import PublicResearcher, DailySearchQuota
    backend = _configured_search()
    if backend is None:
        return None
    base = Path(os.environ['LYA_DATA_DIR']) if os.environ.get('LYA_DATA_DIR') else (
        Path(os.environ['LOCALAPPDATA']) / 'LYA' if os.environ.get('LOCALAPPDATA')
        else Path.home() / '.local' / 'share' / 'LYA')
    return PublicResearcher(backend, DailySearchQuota(base / 'research-usage.sqlite'))
