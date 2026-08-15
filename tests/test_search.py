"""Tests for the search manager: aggregation, deduplication, and
per-provider error isolation (spec section 24)."""

import unittest

from psearch.models import SearchResult
from psearch.providers.base import ProviderError, SearchProvider
from psearch.search import deduplicate, normalize_url, run_search


class _FakeProvider(SearchProvider):
    """A provider stand-in that returns canned results or raises, so
    these tests never touch the network."""

    def __init__(self, name, results=None, exc=None):
        self.name = name
        self._results = results or []
        self._exc = exc

    def search(self, query, limit):
        if self._exc is not None:
            raise self._exc
        return self._results[:limit]


def _result(url, source="Test", title="Title"):
    return SearchResult(title=title, url=url, description="", source=source)


class NormalizeUrlTests(unittest.TestCase):
    def test_lowercases_scheme_and_host(self):
        self.assertEqual(
            normalize_url("HTTPS://Example.COM/Path"),
            "https://example.com/Path",
        )

    def test_drops_trailing_slash(self):
        self.assertEqual(
            normalize_url("https://example.com/path/"),
            normalize_url("https://example.com/path"),
        )

    def test_drops_fragment(self):
        self.assertEqual(
            normalize_url("https://example.com/path#section"),
            normalize_url("https://example.com/path"),
        )

    def test_keeps_distinct_query_strings_distinct(self):
        self.assertNotEqual(
            normalize_url("https://example.com/p?id=2"),
            normalize_url("https://example.com/p?id=3"),
        )


class DeduplicateTests(unittest.TestCase):
    def test_removes_duplicates_keeping_first_occurrence(self):
        # Mirrors spec section 24's example: A, B, A, C, B -> A, B, C
        results = [
            _result("https://example.com/a", source="A"),
            _result("https://example.com/b", source="A"),
            _result("https://example.com/a", source="B"),
            _result("https://example.com/c", source="A"),
            _result("https://example.com/b", source="B"),
        ]
        deduped = deduplicate(results)
        urls = [r.url for r in deduped]
        self.assertEqual(
            urls,
            ["https://example.com/a", "https://example.com/b", "https://example.com/c"],
        )
        self.assertEqual(deduped[0].source, "A")  # first occurrence wins

    def test_treats_trailing_slash_as_duplicate(self):
        results = [_result("https://example.com/x"), _result("https://example.com/x/")]
        self.assertEqual(len(deduplicate(results)), 1)


class RunSearchTests(unittest.TestCase):
    def test_combines_results_from_multiple_providers(self):
        providers = [
            _FakeProvider("A", results=[_result("https://a.example.com")]),
            _FakeProvider("B", results=[_result("https://b.example.com")]),
        ]
        run = run_search("query", providers, limit_per_provider=10)
        self.assertEqual(len(run.results), 2)
        self.assertTrue(all(o.ok for o in run.outcomes))

    def test_one_provider_failing_does_not_affect_others(self):
        providers = [
            _FakeProvider("Good", results=[_result("https://good.example.com")]),
            _FakeProvider("Bad", exc=ProviderError("Bad", "timeout")),
        ]
        run = run_search("query", providers, limit_per_provider=10)

        self.assertEqual(len(run.results), 1)
        self.assertEqual(run.results[0].url, "https://good.example.com")

        outcomes_by_name = {o.provider_name: o for o in run.outcomes}
        self.assertTrue(outcomes_by_name["Good"].ok)
        self.assertFalse(outcomes_by_name["Bad"].ok)
        self.assertEqual(outcomes_by_name["Bad"].error, "timeout")

    def test_unexpected_exception_is_also_isolated(self):
        """Even a bug in a provider (not just a well-behaved
        ProviderError) shouldn't take down the whole search."""
        providers = [
            _FakeProvider("Good", results=[_result("https://good.example.com")]),
            _FakeProvider("Buggy", exc=ValueError("boom")),
        ]
        run = run_search("query", providers, limit_per_provider=10)
        self.assertEqual(len(run.results), 1)
        outcomes_by_name = {o.provider_name: o for o in run.outcomes}
        self.assertFalse(outcomes_by_name["Buggy"].ok)

    def test_deduplicates_across_providers(self):
        providers = [
            _FakeProvider("A", results=[_result("https://same.example.com", source="A")]),
            _FakeProvider("B", results=[_result("https://same.example.com", source="B")]),
        ]
        run = run_search("query", providers, limit_per_provider=10)
        self.assertEqual(len(run.results), 1)

    def test_total_limit_applies_after_deduplication(self):
        providers = [
            _FakeProvider(
                "A",
                results=[_result(f"https://example.com/{i}") for i in range(5)],
            )
        ]
        run = run_search("query", providers, limit_per_provider=10, total_limit=2)
        self.assertEqual(len(run.results), 2)

    def test_per_provider_limit_is_passed_through(self):
        providers = [
            _FakeProvider(
                "A",
                results=[_result(f"https://example.com/{i}") for i in range(5)],
            )
        ]
        run = run_search("query", providers, limit_per_provider=2)
        self.assertEqual(len(run.results), 2)


if __name__ == "__main__":
    unittest.main()
