"""Search manager: runs providers, combines, and deduplicates results.

This module implements the middle of the pipeline described in the
spec (section 6):

    providers -> normalization -> deduplication

It intentionally knows nothing about argparse or terminal output, and
nothing about any single provider's internals — it only depends on
the ``SearchProvider`` interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

from psearch.models import SearchResult
from psearch.providers.base import ProviderError, SearchProvider


@dataclass
class ProviderOutcome:
    """Records whether one provider succeeded or failed, for reporting
    back to the user (the ✓/✗ list from spec section 12)."""

    provider_name: str
    ok: bool
    error: str | None = None
    result_count: int = 0


@dataclass
class SearchRun:
    """Everything a single ``psearch <query>`` invocation produced."""

    query: str
    results: list[SearchResult] = field(default_factory=list)
    outcomes: list[ProviderOutcome] = field(default_factory=list)


def normalize_url(url: str) -> str:
    """Reduce a URL to a form suitable for duplicate detection.

    This is deliberately simple (spec section 14: "basic MVP
    strategy: normalized URL -> unique result"), not a full
    canonicalization library:

    - lowercase the scheme and host (paths stay case-sensitive)
    - drop a trailing slash
    - drop the fragment (``#section``), since it doesn't identify a
      different page
    - keep the query string, since ``?id=2`` is often a genuinely
      different page than ``?id=3``
    """
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def deduplicate(results: list[SearchResult]) -> list[SearchResult]:
    """Remove results with duplicate (normalized) URLs, keeping the
    first occurrence. Provider order is otherwise preserved (spec
    section 21: ranking just preserves provider ordering for the
    MVP)."""
    seen: set[str] = set()
    unique: list[SearchResult] = []
    for result in results:
        key = normalize_url(result.url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return unique


def run_search(
    query: str,
    providers: list[SearchProvider],
    limit_per_provider: int,
    total_limit: int | None = None,
) -> SearchRun:
    """Query every provider synchronously, one at a time (spec
    section 11), tolerating individual provider failures (spec
    section 12) so one bad provider never breaks the whole search.
    """
    all_results: list[SearchResult] = []
    outcomes: list[ProviderOutcome] = []

    for provider in providers:
        try:
            provider_results = provider.search(query, limit_per_provider)
        except ProviderError as exc:
            outcomes.append(
                ProviderOutcome(provider_name=provider.name, ok=False, error=exc.reason)
            )
            continue
        except Exception as exc:  # noqa: BLE001 - a provider must never take down the run
            outcomes.append(
                ProviderOutcome(provider_name=provider.name, ok=False, error=str(exc))
            )
            continue

        outcomes.append(
            ProviderOutcome(
                provider_name=provider.name, ok=True, result_count=len(provider_results)
            )
        )
        all_results.extend(provider_results)

    deduped = deduplicate(all_results)
    if total_limit is not None:
        deduped = deduped[:total_limit]

    return SearchRun(query=query, results=deduped, outcomes=outcomes)
