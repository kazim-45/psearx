"""Provider interface.

A provider is anything that can turn a text query into a list of
``SearchResult`` objects (spec section 9). The search manager
(``search.py``) only ever talks to this interface — it does not know
or care whether a given provider works by scraping HTML, calling a
JSON API, or something else entirely.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from psearch.models import SearchResult


class SearchProvider(ABC):
    """Base class every search provider must implement."""

    #: Human-readable name shown to the user (e.g. in "Source: X"
    #: and in provider-status / error messages).
    name: str

    @abstractmethod
    def search(self, query: str, limit: int) -> list[SearchResult]:
        """Run a search and return up to ``limit`` normalized results.

        Implementations should raise ``ProviderError`` (or let a
        lower-level exception propagate) rather than swallowing
        failures — the search manager is responsible for catching
        errors so that one provider's failure never takes down the
        others (spec section 12).
        """
        raise NotImplementedError


class ProviderError(Exception):
    """Raised by a provider when a search could not be completed.

    Providers should wrap lower-level exceptions (network errors,
    unexpected HTTP statuses, parsing failures, missing
    configuration, etc.) in this so the search manager and CLI have
    one exception type to handle without needing to know the
    internals of every provider.
    """

    def __init__(self, provider: str, reason: str):
        self.provider = provider
        self.reason = reason
        super().__init__(f"{provider}: {reason}")
