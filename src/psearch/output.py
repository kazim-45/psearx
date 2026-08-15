"""Terminal output formatting.

Plain text, no colors, no external formatting libraries (spec
sections 17-18). Search results are untrusted input (spec section
23), so this module only ever treats them as text to print — nothing
here interprets HTML, executes anything, or follows a link.
"""

from __future__ import annotations

from psearch.search import ProviderOutcome, SearchRun

_DIVIDER = "─" * 46


def format_provider_status(outcomes: list[ProviderOutcome]) -> str:
    """The ✓/✗ per-provider status list printed before results
    (spec section 12)."""
    lines = ["Searching..."]
    for outcome in outcomes:
        if outcome.ok:
            lines.append(f"✓ {outcome.provider_name}")
        else:
            lines.append(f"✗ {outcome.provider_name} — {outcome.error}")
    return "\n".join(lines)


def format_results(run: SearchRun) -> str:
    """The main results listing (spec section 17)."""
    lines = ["PrivateSearch", _DIVIDER, "", f"Query: {run.query}", ""]

    if not run.results:
        lines.append("No results.")
    else:
        for index, result in enumerate(run.results, start=1):
            lines.append(f"[{index}] {result.title}")
            lines.append(f"    {result.url}")
            if result.description:
                lines.append(f"    {result.description}")
            lines.append(f"    Source: {result.source}")
            lines.append("")

    lines.append(_DIVIDER)
    count = len(run.results)
    noun = "result" if count == 1 else "results"
    lines.append(f"{count} {noun}")

    return "\n".join(lines)
