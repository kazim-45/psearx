# psearch — Private CLI Meta-Search

A small, privacy-focused CLI metasearch tool, inspired by [SearXNG](https://github.com/searxng/searxng).

`psearch` sends your query to a few search providers one at a time, merges and
deduplicates the results, and prints them to your terminal. No accounts, no
browser, no config file, no database.

```
$ psearch "linux networking books"

PrivateSearch
──────────────────────────────────────────────

Query: linux networking books

[1] Linux Network Programming
    https://example.com/linux-networking
    Learn Linux networking and socket programming...
    Source: DuckDuckGo

[2] TCP/IP Illustrated
    https://example.org/tcpip
    A comprehensive guide to TCP/IP...
    Source: Brave

──────────────────────────────────────────────
2 results
```

## Install

```bash
git clone https://github.com/kazim-45/psearx.git
cd psearx
pip install -e .
```

This installs the `psearch` command (via the `[project.scripts]` entry point
in `pyproject.toml`) along with its two dependencies: `requests` and
`beautifulsoup4`.

## Usage

```bash
psearch "python sockets"
psearch "python sockets" --limit 10
psearch "python sockets" --engines brave,wikipedia
psearch --help
```

| Flag | Meaning |
|---|---|
| `--limit N` | Max results shown after deduplication (default: unlimited) |
| `--per-provider-limit N` | Max results requested from each provider (default: 10) |
| `--engines a,b,c` | Which providers to use (default: `duckduckgo,brave,wikipedia`) |

Per-provider status (✓/✗) is printed to **stderr**, and the results listing to
**stdout** — so `psearch "query" > results.txt` gives you a clean file with
just the results.

### Brave

Brave's provider uses their official Web Search API, which needs a free API
key: sign up at <https://api.search.brave.com/>, then:

```bash
export BRAVE_API_KEY="your-key-here"
```

If the key isn't set, Brave just shows up as a failed provider (like a
timeout would) — the rest of the search still runs and prints normally. It's
never required.

## Privacy

- **Stores nothing by default.** No search history, no cache, no database.
- **No analytics or telemetry.** Nothing is sent anywhere except the search
  providers you query.
- **No account required.**
- **No JavaScript execution.** Results are treated as plain text data, never
  as code or markup to render.

The honest version of the privacy claim is:

> The CLI does not intentionally track or store your searches.

**Not:**

> Your searches are completely anonymous.

```
Your CLI
    │
    ▼
Search provider
```

`psearch` doesn't track you, but whatever you search for is still sent to
DuckDuckGo, Brave, or Wikipedia, and each of those may log it according to
its own privacy policy. That's true of any metasearch tool and is outside
what a client-side CLI can control.

## Architecture

```
CLI input → query → providers → results → deduplication → output
```

```
src/psearch/
├── cli.py              # argument parsing, wiring, entry point
├── search.py           # runs providers synchronously, deduplicates
├── models.py            # the SearchResult data model
├── output.py            # terminal formatting
└── providers/
    ├── base.py          # SearchProvider interface + ProviderError
    ├── duckduckgo.py    # scrapes html.duckduckgo.com/html/
    ├── brave.py         # calls the official Brave Web Search API
    └── wikipedia.py     # calls the official MediaWiki search API
```

Every provider implements one method — `search(query, limit) -> list[SearchResult]`
— and the rest of the app only ever talks to that interface. Adding a new
provider means adding one new file plus one line in `providers/__init__.py`;
nothing else in the codebase needs to change.

Searches run **synchronously**, one provider at a time, on purpose — see spec
section 11. Concurrency is a deliberate non-goal for v0.1 so the networking
stays easy to follow; it's the natural first thing to add in v0.2.

## Error handling

One provider failing (timeout, HTTP error, malformed response, missing API
key, ...) never stops the others:

```
Searching...
✓ DuckDuckGo
✗ Brave — BRAVE_API_KEY is not set (get a free key at https://api.search.brave.com/)
✓ Wikipedia
```

Every network request has an 8-second timeout.

## Known limitations

- **DuckDuckGo's provider scrapes HTML**, not a documented API, because
  DuckDuckGo doesn't offer a free, keyless web-search API. That HTML page can
  change its markup at any time, which would break `providers/duckduckgo.py`
  specifically — the rest of the app is unaffected (that's the point of the
  provider abstraction). This project was built without live network access
  to DuckDuckGo, so the CSS selectors in `_parse_html` were written to match
  DuckDuckGo's generally-documented-elsewhere HTML structure rather than
  verified against a live response — run it and check `tests/test_providers.py`
  against the real page if it comes back empty.
- **Brave requires a free API key.** There's no way around this — Brave
  doesn't offer anonymous, keyless search.
- Deduplication is a simple normalized-URL match (scheme/host lowercased,
  trailing slash and `#fragment` dropped). It won't catch two different URLs
  that happen to serve the same content.

## Testing

```bash
python -m unittest discover -s tests
```

(or `pytest`, if you have it installed — the tests are plain
`unittest.TestCase` classes, so both work.)

Tests cover provider response parsing (against static fixtures, not live
requests), URL normalization, deduplication, per-provider error isolation,
and output formatting.

## Non-goals

This is intentionally not: Google, Bing, a web crawler, a full search index,
a browser, a GUI, a recommendation engine, an AI search assistant, or a
distributed system. See the spec's guiding principle:

> Simple enough that one person can understand the entire codebase.

## Roadmap

v0.1 (this): synchronous providers, normalization, deduplication, CLI.
Later: async/concurrent requests, better ranking, a config file, caching,
pagination, custom providers. Each version should solve a real problem
rather than add complexity for its own sake.

## License

MIT — see `LICENSE`.
