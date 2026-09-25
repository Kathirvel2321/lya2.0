"""Isolated hybrid research-adapter tests. No key or network is used."""
from datetime import datetime, timezone
import json
import unittest
from unittest.mock import patch

from brain.research import (ENDPOINT, HybridSearch, TavilySearch, YouSearchMCP,
                            default_researcher)


class Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit):
        return self.payload[:limit]


class ResponseBytes(Response):
    def __init__(self, payload):
        self.payload = payload


class BytesOpener:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []
    def open(self, request, timeout):
        self.calls.append((request, timeout))
        return ResponseBytes(self.payload)


class Opener:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []
    def open(self, request, timeout):
        self.calls.append((request, timeout))
        return Response(self.payload)


class SearchStub:
    def __init__(self, label):
        self.label = label
        self.calls = []
    def __call__(self, query, **limits):
        self.calls.append((query, limits))
        return [{
            "id": "source-1",
            "url": f"https://{self.label}.example/report",
            "retrieved_at": "2026-09-20T00:00:00Z",
            "claim": self.label,
            "excerpt": self.label,
        }]


class ResearchAdapterChecks(unittest.TestCase):
    def payload(self, url="https://example.invalid/report", content="Atlas launched today."):
        return {"results": [{"title": "Example", "url": url, "content": content,
                             "score": 0.9}], "usage": {"credits": 1}}

    def test_returns_bounded_result_with_key_only_in_header(self):
        opener = Opener(self.payload())
        adapter = TavilySearch("FAKE_KEY", opener=opener,
            clock=lambda: datetime(2026, 9, 20, tzinfo=timezone.utc))
        records = adapter("public fixture", max_sources=6, max_bytes=8000, timeout=8)
        self.assertEqual(records, [{
            "id": "source-1",
            "url": "https://example.invalid/report",
            "retrieved_at": "2026-09-20T00:00:00Z",
            "claim": "Atlas launched today.",
            "excerpt": "Atlas launched today.",
        }])
        request, timeout = opener.calls[0]
        self.assertEqual((request.full_url, timeout), (ENDPOINT, 8))
        self.assertEqual(request.get_header("Authorization"), "Bearer FAKE_KEY")
        self.assertNotIn("FAKE_KEY", request.full_url)
        sent = json.loads(request.data)
        self.assertEqual((sent["search_depth"], sent["chunks_per_source"]), ("basic", 1))
        self.assertFalse(sent["include_answer"])
        self.assertFalse(sent["include_raw_content"])

    def test_rejects_missing_results_and_non_https_source(self):
        for payload in ({"results": []}, self.payload("http://example.invalid/report")):
            with self.subTest(payload=payload):
                adapter = TavilySearch("FAKE", opener=Opener(payload))
                with self.assertRaises(ValueError):
                    adapter("fixture", max_sources=6, max_bytes=8000, timeout=8)

    def test_default_adapter_requires_both_explicit_safety_flags(self):
        values = {
            "LYA_TAVILY_RESEARCH_ENABLED": "1",
            "LYA_TAVILY_FREE_ONLY": "1",
            "TAVILY_API_KEY": "FAKE",
        }
        with patch("brain.research._setting", side_effect=lambda name: values.get(name)):
            self.assertIsInstance(default_researcher(), TavilySearch)
        values["LYA_TAVILY_FREE_ONLY"] = "0"
        with patch("brain.research._setting", side_effect=lambda name: values.get(name)):
            self.assertIsNone(default_researcher())

    def test_rejects_oversize_query_and_unsafe_limits(self):
        adapter = TavilySearch("FAKE", opener=Opener(self.payload()))
        with self.assertRaises(ValueError):
            adapter("x" * 2001, max_sources=6, max_bytes=8000, timeout=8)
        with self.assertRaises(ValueError):
            adapter("fixture", max_sources=7, max_bytes=8000, timeout=8)
        with self.assertRaises(ValueError):
            adapter("fixture", max_sources=6, max_bytes=8000, timeout=9)

    def test_keyless_you_mcp_returns_bounded_sources(self):
        result = {"results": {"web": [{
            "url": "https://docs.example/report",
            "description": "Verified description.",
            "snippets": ["Supporting snippet."],
        }]}}
        payload = ("event: message\n" + "data: " + json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "result": {"structuredContent": result},
        }) + "\n").encode()
        opener = BytesOpener(payload)
        adapter = YouSearchMCP(opener=opener,
            clock=lambda: datetime(2026, 9, 20, tzinfo=timezone.utc))
        records = adapter("public fixture", max_sources=6, max_bytes=8000, timeout=8)
        self.assertEqual(records[0]["url"], "https://docs.example/report")
        self.assertIn("Supporting snippet.", records[0]["excerpt"])
        request, timeout = opener.calls[0]
        self.assertEqual(timeout, 8)
        self.assertTrue(request.get_header("User-agent").startswith("LYA/"))

    def test_hybrid_spends_tavily_only_for_explicit_critical_research(self):
        free, tavily = SearchStub("free"), SearchStub("tavily")
        adapter = HybridSearch(free, tavily, monotonic=lambda: 0)
        normal = adapter("research a public topic", max_sources=6,
                         max_bytes=8000, timeout=8)
        self.assertEqual([record["claim"] for record in normal], ["free"])
        self.assertEqual(len(tavily.calls), 0)
        critical = adapter("critical research: public topic", max_sources=6,
                           max_bytes=8000, timeout=8)
        self.assertEqual([record["claim"] for record in critical], ["tavily", "free"])
        self.assertEqual(tavily.calls[0][0], "public topic")

    def test_default_prefers_free_hybrid_without_a_key(self):
        values = {"LYA_FREE_RESEARCH_ENABLED": "1"}
        with patch("brain.research._setting", side_effect=lambda name: values.get(name)):
            self.assertIsInstance(default_researcher(), HybridSearch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
