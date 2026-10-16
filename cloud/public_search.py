"""Search-only You.com MCP adapter, shared by public research clients.

The keyless free profile is documented for evaluation. It supplies snippets,
not independent fact verification or page extraction. No provider key is used.
"""
from datetime import datetime, timezone
import json
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit

YOU_ENDPOINT = "https://api.you.com/mcp?profile=free"
MAX_RESPONSE_BYTES = 131072


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class YouSearchMCP:
    """Use You.com's keyless, search-only MCP profile for routine public research."""

    def __init__(self, opener=None, clock=None):
        self.opener = opener or urllib.request.build_opener(NoRedirect())
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def __call__(self, query, *, max_sources, max_bytes, timeout):
        if not isinstance(query, str) or not query.strip() or len(query) > 400:
            raise ValueError("Research query is invalid.")
        if type(max_sources) is not int or not 1 <= max_sources <= 6:
            raise ValueError("Research source limit is invalid.")
        if type(max_bytes) is not int or not 512 <= max_bytes <= 8000:
            raise ValueError("Research byte limit is invalid.")
        if not isinstance(timeout, (int, float)) or not 1 <= timeout <= 8:
            raise ValueError("Research timeout is invalid.")

        body = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "you-search",
                "arguments": {
                    "query": query.strip(),
                    "count": max_sources,
                    "extraction": "none",
                },
            },
        }, separators=(",", ":")).encode()
        request = urllib.request.Request(
            YOU_ENDPOINT, data=body, method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-06-18",
                "User-Agent": "LYA/0.1 public-research",
            },
        )
        try:
            with self.opener.open(request, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except (OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
            raise ValueError("Free public research provider is unavailable.") from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Free public research response is too large.")

        payload = self._mcp_payload(raw)
        result = payload.get("result")
        if not isinstance(result, dict) or result.get("isError") is True:
            raise ValueError("Free public research returned an error.")
        structured = result.get("structuredContent")
        if not isinstance(structured, dict):
            structured = self._text_payload(result.get("content"))
        groups = structured.get("results") if isinstance(structured, dict) else None
        if not isinstance(groups, dict):
            raise ValueError("Free public research returned invalid data.")

        items = []
        for group in ("web", "news"):
            values = groups.get(group, [])
            if isinstance(values, list):
                items.extend(values)
        return _search_records(items, self.clock, max_sources, max_bytes)

    @staticmethod
    def _mcp_payload(raw):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Free public research returned invalid data.") from exc
        candidates = []
        for line in text.splitlines():
            value = line[5:].strip() if line.startswith("data:") else line.strip()
            if not value or value.startswith("event:"):
                continue
            try:
                message = json.loads(value)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict) and message.get("id") == 1:
                candidates.append(message)
        if not candidates:
            raise ValueError("Free public research returned invalid MCP data.")
        return candidates[-1]

    @staticmethod
    def _text_payload(content):
        if not isinstance(content, list):
            return {}
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            try:
                value = json.loads(block.get("text", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(value, dict):
                return value
        return {}


def _search_records(items, clock, max_sources, max_bytes):
    stamp = clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    records, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str):
            continue
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            continue
        url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
        description = item.get("description", "")
        parts = [description if isinstance(description, str) else ""]
        snippets = item.get("snippets", [])
        if isinstance(snippets, list):
            parts.extend(value for value in snippets if isinstance(value, str))
        excerpt = " ".join(" ".join(parts).split())[:2000]
        if url in seen or not excerpt:
            continue
        record = {
            "id": f"source-{len(records) + 1}",
            "url": url,
            "retrieved_at": stamp,
            "claim": excerpt[:300],
            "excerpt": excerpt,
        }
        encoded = json.dumps(records + [record], ensure_ascii=False,
                             separators=(",", ":")).encode()
        if len(encoded) > max_bytes:
            continue
        records.append(record)
        seen.add(url)
        if len(records) >= max_sources:
            break
    if not records:
        raise ValueError("Free public research returned no usable HTTPS sources.")
    return records


