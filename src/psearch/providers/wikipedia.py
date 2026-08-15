"""Wikipedia provider.

Uses the official MediaWiki search API (no API key required):
https://www.mediawiki.org/wiki/API:Search

This is the most stable of the MVP providers, since it's a
documented, versioned JSON API rather than scraped HTML.
"""

from __future__ import annotations

import re

import requests

from psearch.models import SearchResult
from psearch.providers.base import ProviderError, SearchProvider

_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
_TIMEOUT_SECONDS = 8
_USER_AGENT = "psearch/0.1 (https://github.com/example/private-search)"

_TAG_RE = re.compile(r"<[^>]+>")


class WikipediaProvider(SearchProvider):
    name = "Wikipedia"

    def search(self, query: str, limit: int) -> list[SearchResult]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": max(1, min(limit, 50)),
            "format": "json",
        }
        try:
            response = requests.get(
                _SEARCH_URL,
                params=params,
                headers={"User-Agent": _USER_AGENT},
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ProviderError(self.name, str(exc)) from exc
        except ValueError as exc:  # invalid JSON
            raise ProviderError(self.name, f"invalid response: {exc}") from exc

        try:
            return _parse_payload(payload, limit)
        except (KeyError, TypeError) as exc:
            raise ProviderError(self.name, f"unexpected response shape: {exc}") from exc


def _strip_html(text: str) -> str:
    """Wikipedia's ``snippet`` field contains raw HTML (e.g.
    ``<span class="searchmatch">``) to highlight matched terms. We
    treat it as untrusted data and strip it to plain text rather than
    rendering it (spec section 23: search results are untrusted
    input)."""
    return _TAG_RE.sub("", text)


def _parse_payload(payload: dict, limit: int) -> list[SearchResult]:
    """Turn a raw MediaWiki API response into normalized
    SearchResults. Kept free of any network code so it can be unit
    tested against a static fixture."""
    entries = payload["query"]["search"]
    results = []
    for entry in entries[:limit]:
        title = entry["title"]
        url = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
        results.append(
            SearchResult(
                title=title,
                url=url,
                description=_strip_html(entry.get("snippet", "")),
                source="Wikipedia",
            )
        )
    return results
