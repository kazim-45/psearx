"""Provider tests.

These test the *parsing* logic in each provider against small,
static fixtures — they never make a real network request, so they
run without network access and won't fail just because a provider
happens to be down (spec section 24: "test that a provider can turn
a response into a SearchResult").
"""

import unittest

from psearch.providers.brave import _parse_payload as brave_parse_payload
from psearch.providers.duckduckgo import _parse_html, _unwrap_redirect
from psearch.providers.wikipedia import _parse_payload as wikipedia_parse_payload
from psearch.providers.wikipedia import _strip_html


class DuckDuckGoParsingTests(unittest.TestCase):
    HTML = """
    <div class="results">
      <div class="result results_links results_links_deep web-result">
        <div class="links_main links_deep result__body">
          <h2 class="result__title">
            <a rel="nofollow" class="result__a"
               href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage&rut=1">
               Example Title
            </a>
          </h2>
          <a class="result__snippet" href="//duckduckgo.com/l/?uddg=x">
            An example <b>snippet</b> with markup.
          </a>
        </div>
      </div>
      <div class="result results_links results_links_deep web-result">
        <div class="links_main links_deep result__body">
          <h2 class="result__title">
            <a rel="nofollow" class="result__a" href="https://direct.example.com/">
               Direct Link Result
            </a>
          </h2>
        </div>
      </div>
    </div>
    """

    def test_parses_title_url_and_snippet(self):
        results = _parse_html(self.HTML, limit=10)
        self.assertEqual(len(results), 2)

        first = results[0]
        self.assertEqual(first.title, "Example Title")
        self.assertEqual(first.url, "https://example.com/page")
        self.assertIn("example", first.description.lower())
        self.assertEqual(first.source, "DuckDuckGo")

    def test_handles_result_with_no_snippet(self):
        results = _parse_html(self.HTML, limit=10)
        second = results[1]
        self.assertEqual(second.description, "")
        self.assertEqual(second.url, "https://direct.example.com/")

    def test_respects_limit(self):
        results = _parse_html(self.HTML, limit=1)
        self.assertEqual(len(results), 1)

    def test_unwrap_redirect_passes_through_direct_links(self):
        self.assertEqual(
            _unwrap_redirect("https://example.com/direct"),
            "https://example.com/direct",
        )

    def test_unwrap_redirect_extracts_real_url(self):
        href = "//duckduckgo.com/l/?uddg=https%3A%2F%2Ffoo.com%2Fbar&rut=x"
        self.assertEqual(_unwrap_redirect(href), "https://foo.com/bar")


class WikipediaParsingTests(unittest.TestCase):
    PAYLOAD = {
        "query": {
            "search": [
                {
                    "title": "Linux",
                    "snippet": 'An open-source <span class="searchmatch">operating</span> system.',
                    "pageid": 1,
                },
                {
                    "title": "Linux kernel",
                    "snippet": 'The <span class="searchmatch">kernel</span> at the core of Linux.',
                    "pageid": 2,
                },
            ]
        }
    }

    def test_parses_title_and_builds_url(self):
        results = wikipedia_parse_payload(self.PAYLOAD, limit=10)
        self.assertEqual(results[0].title, "Linux")
        self.assertEqual(results[0].url, "https://en.wikipedia.org/wiki/Linux")
        self.assertEqual(results[0].source, "Wikipedia")

    def test_url_replaces_spaces_with_underscores(self):
        results = wikipedia_parse_payload(self.PAYLOAD, limit=10)
        self.assertEqual(results[1].url, "https://en.wikipedia.org/wiki/Linux_kernel")

    def test_strips_html_from_snippet(self):
        results = wikipedia_parse_payload(self.PAYLOAD, limit=10)
        self.assertNotIn("<span", results[0].description)
        self.assertIn("operating", results[0].description)

    def test_respects_limit(self):
        results = wikipedia_parse_payload(self.PAYLOAD, limit=1)
        self.assertEqual(len(results), 1)

    def test_strip_html_helper(self):
        self.assertEqual(_strip_html("<b>bold</b> text"), "bold text")


class BraveParsingTests(unittest.TestCase):
    PAYLOAD = {
        "web": {
            "results": [
                {
                    "title": "Example Result",
                    "url": "https://example.com/one",
                    "description": "A description.",
                },
                {
                    "title": "Second Result",
                    "url": "https://example.com/two",
                    "description": "",
                },
            ]
        }
    }

    def test_parses_results(self):
        results = brave_parse_payload(self.PAYLOAD, limit=10)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "Example Result")
        self.assertEqual(results[0].url, "https://example.com/one")
        self.assertEqual(results[0].source, "Brave")

    def test_respects_limit(self):
        results = brave_parse_payload(self.PAYLOAD, limit=1)
        self.assertEqual(len(results), 1)

    def test_handles_missing_results_key_gracefully(self):
        results = brave_parse_payload({"web": {}}, limit=10)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
