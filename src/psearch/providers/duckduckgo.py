"""DuckDuckGo provider.

DuckDuckGo does not offer a public, keyless API for general web
search. This provider uses DuckDuckGo's lightweight HTML results page
(``html.duckduckgo.com/html/``), a plain, mostly-static page meant for
non-JS clients — the same kind of endpoint other open-source terminal
search tools rely on.

Because this is HTML scraping rather than a documented API, this is
the single most likely provider to break if DuckDuckGo changes their
markup. If that happens, only this file should need to change (spec
section 20) — the ``_parse_html`` function below is kept separate
from the network call specifically so it can be tested and fixed in
isolation.

NOTE: the HTML fixture used in tests/test_providers.py was written to
match this parser, not captured live from DuckDuckGo (this project
was built in a sandboxed environment without network access). Treat
the selectors below as a reasonable starting point and re-check them
against a real response the first time you run this.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from psearch.models import SearchResult
from psearch.providers.base import ProviderError, SearchProvider

_SEARCH_URL = "https://html.duckduckgo.com/html/"
_TIMEOUT_SECONDS = 8
_USER_AGENT = (
    "Mozilla/5.0 (compatible; psearch/0.1; "
    "+https://github.com/example/private-search)"
)


class DuckDuckGoProvider(SearchProvider):
    name = "DuckDuckGo"

    def search(self, query: str, limit: int) -> list[SearchResult]:
        try:
            response = requests.post(
                _SEARCH_URL,
                data={"q": query},
                headers={"User-Agent": _USER_AGENT},
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(self.name, str(exc)) from exc

        try:
            return _parse_html(response.text, limit)
        except Exception as exc:  # noqa: BLE001 - untrusted HTML, be defensive
            raise ProviderError(self.name, f"failed to parse response: {exc}") from exc


def _unwrap_redirect(href: str) -> str:
    """DuckDuckGo's HTML results link to ``/l/?uddg=<real-url>``
    rather than linking directly. Pull the real URL back out; if the
    link isn't a redirect (or is malformed), fall back to the href
    as-is rather than raising."""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if parsed.path == "/l/":
        real_url = parse_qs(parsed.query).get("uddg")
        if real_url:
            return real_url[0]
    return href


def _parse_html(html: str, limit: int) -> list[SearchResult]:
    """Turn a raw HTML results page into normalized SearchResults.

    Kept free of any network code so it can be unit tested against a
    static fixture (spec section 24: provider tests).
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []

    for result_div in soup.find_all("div", class_="result"):
        link = result_div.find("a", class_="result__a")
        if link is None or not link.get("href"):
            continue

        snippet_el = result_div.find(class_="result__snippet")
        description = snippet_el.get_text(" ", strip=True) if snippet_el else ""

        results.append(
            SearchResult(
                title=link.get_text(" ", strip=True),
                url=_unwrap_redirect(link["href"]),
                description=description,
                source="DuckDuckGo",
            )
        )

        if len(results) >= limit:
            break

    return results
