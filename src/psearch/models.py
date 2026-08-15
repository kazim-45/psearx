"""Core data model shared by every search provider.

Every provider, no matter how it talks to its search engine, must
translate its provider-specific response into this one shape before
handing results back to the rest of the application. Nothing outside
``providers/`` should ever see a provider's raw response format
(spec section 8).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    """A single, normalized search result."""

    title: str
    url: str
    description: str
    source: str

    def __post_init__(self) -> None:
        # Guard against a provider accidentally handing back an
        # empty/missing URL, which would silently break
        # deduplication and display downstream.
        if not self.url:
            raise ValueError("SearchResult requires a non-empty url")
