"""Output formatting tests."""

import unittest

from psearch.models import SearchResult
from psearch.output import format_provider_status, format_results
from psearch.search import ProviderOutcome, SearchRun


class FormatResultsTests(unittest.TestCase):
    def test_includes_query_title_url_and_source(self):
        run = SearchRun(
            query="linux networking",
            results=[
                SearchResult(
                    title="Linux Networking Guide",
                    url="https://example.com/linux",
                    description="A guide to Linux networking.",
                    source="DuckDuckGo",
                )
            ],
        )
        output = format_results(run)

        self.assertIn("Query: linux networking", output)
        self.assertIn("[1] Linux Networking Guide", output)
        self.assertIn("https://example.com/linux", output)
        self.assertIn("Source: DuckDuckGo", output)
        self.assertIn("1 result", output)
        self.assertNotIn("1 results", output)

    def test_handles_zero_results(self):
        run = SearchRun(query="asdkfjhaslkdjfh")
        output = format_results(run)
        self.assertIn("No results.", output)
        self.assertIn("0 results", output)

    def test_pluralizes_result_count(self):
        results = [
            SearchResult(
                title=f"T{i}", url=f"https://example.com/{i}", description="", source="X"
            )
            for i in range(3)
        ]
        run = SearchRun(query="q", results=results)
        output = format_results(run)
        self.assertIn("3 results", output)


class FormatProviderStatusTests(unittest.TestCase):
    def test_shows_check_for_success_and_x_for_failure(self):
        outcomes = [
            ProviderOutcome(provider_name="DuckDuckGo", ok=True, result_count=5),
            ProviderOutcome(provider_name="Brave", ok=False, error="timeout"),
        ]
        status = format_provider_status(outcomes)
        self.assertIn("✓ DuckDuckGo", status)
        self.assertIn("✗ Brave — timeout", status)


if __name__ == "__main__":
    unittest.main()
