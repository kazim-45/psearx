"""Brave Search provider.

Uses Brave's official Web Search API:
https://api.search.brave.com/app/documentation/web-search/get-started

This requires an API key (Brave offers a free tier). The key is read
from the ``BRAVE_API_KEY`` environment variable — it is never
hardcoded, logged, written to disk, or sent anywhere except to
Brave's own API endpoint.

If the key isn't set, this provider fails the same way any other
provider failure is handled (spec section 12): it's reported as a
single failed provider with a clear reason, and the rest of the
search still runs and displays normally.
"""

from __future__ import annotations

import os

import requests

from psearch.models import SearchResult
from psearch.providers.base import ProviderError, SearchProvider

_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_TIMEOUT_SECONDS = 8
_API_KEY_ENV_VAR = "BRAVE_API_KEY"


class BraveProvider(SearchProvider):
    name = "Brave"

    def search(self, query: str, limit: int) -> list[SearchResult]:
        api_key = os.environ.get(_API_KEY_ENV_VAR)
        if not api_key:
            raise ProviderError(
                self.name,
                f"{_API_KEY_ENV_VAR} is not set (get a free key at "
                "https://api.search.brave.com/)",
            )

        try:
            response = requests.get(
                _SEARCH_URL,
                params={"q": query, "count": max(1, min(limit, 20))},
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                },
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


def _parse_payload(payload: dict, limit: int) -> list[SearchResult]:
    """Turn a raw Brave API response into normalized SearchResults.
    Kept free of any network code so it can be unit tested against a
    static fixture."""
    entries = payload.get("web", {}).get("results", [])
    results = []
    for entry in entries[:limit]:
        results.append(
            SearchResult(
                title=entry.get("title", "").strip(),
                url=entry["url"],
                description=entry.get("description", "").strip(),
                source="Brave",
            )
        )
    return results
