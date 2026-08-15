"""psearch: a small, privacy-focused CLI metasearch tool.

See README.md for usage. Each module's docstring explains how the
pieces fit together:

    cli.py        -> argument parsing, wiring, entry point
    search.py     -> runs providers, deduplicates
    models.py     -> the SearchResult data model
    output.py     -> terminal formatting
    providers/    -> one module per search engine
"""

__version__ = "0.1.0"
