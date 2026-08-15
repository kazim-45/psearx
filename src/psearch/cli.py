"""Command-line entry point.

Parses arguments, builds the requested providers, runs the search,
and prints the result. Deliberately thin (spec section 16: "keep the
interface minimal") so the pipeline in spec section 28 stays easy to
trace: CLI input -> query -> providers -> results -> deduplication ->
output.
"""

from __future__ import annotations

import argparse
import sys

from psearch.output import format_provider_status, format_results
from psearch.providers import DEFAULT_PROVIDERS, PROVIDER_REGISTRY
from psearch.search import run_search

_DEFAULT_LIMIT_PER_PROVIDER = 10


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="psearch",
        description=(
            "Search the web from the terminal without trackers, accounts, "
            "telemetry, or bloated interfaces. External search providers "
            "may still log your query according to their own policies — "
            "psearch itself does not store or transmit it anywhere else."
        ),
    )
    parser.add_argument("query", help="the search query")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="max results to display after deduplication (default: unlimited)",
    )
    parser.add_argument(
        "--per-provider-limit",
        type=int,
        default=_DEFAULT_LIMIT_PER_PROVIDER,
        metavar="N",
        help=f"max results requested per provider (default: {_DEFAULT_LIMIT_PER_PROVIDER})",
    )
    parser.add_argument(
        "--engines",
        default=None,
        metavar="NAMES",
        help=(
            "comma-separated list of providers to use "
            f"(default: {','.join(DEFAULT_PROVIDERS)}). "
            f"Available: {','.join(sorted(PROVIDER_REGISTRY))}"
        ),
    )
    return parser


def _resolve_providers(engines_arg: str | None) -> list[str]:
    if engines_arg is None:
        return list(DEFAULT_PROVIDERS)

    names = [name.strip().lower() for name in engines_arg.split(",") if name.strip()]
    unknown = [name for name in names if name not in PROVIDER_REGISTRY]
    if unknown:
        available = ", ".join(sorted(PROVIDER_REGISTRY))
        raise SystemExit(
            f"psearch: unknown engine(s): {', '.join(unknown)}. Available: {available}"
        )
    if not names:
        raise SystemExit("psearch: --engines was given but no engine names were found")
    return names


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    query = args.query.strip()
    if not query:
        parser.error("query must not be empty")

    provider_names = _resolve_providers(args.engines)
    providers = [PROVIDER_REGISTRY[name]() for name in provider_names]

    run = run_search(
        query=query,
        providers=providers,
        limit_per_provider=args.per_provider_limit,
        total_limit=args.limit,
    )

    # Provider status goes to stderr, results to stdout, so results
    # can be piped/redirected cleanly (e.g. `psearch foo > out.txt`)
    # without the status lines mixed in.
    print(format_provider_status(run.outcomes), file=sys.stderr)
    print(file=sys.stderr)
    print(format_results(run))

    return 0


if __name__ == "__main__":
    sys.exit(main())
