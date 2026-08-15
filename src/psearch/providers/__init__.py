"""Search providers.

Each module here implements ``SearchProvider`` (see
``providers/base.py``) for one search engine. The rest of the
application never imports a provider-specific module directly —
it goes through the registry below (spec section 19: providers
should be isolated from the core application).
"""

from __future__ import annotations

from psearch.providers.brave import BraveProvider
from psearch.providers.duckduckgo import DuckDuckGoProvider
from psearch.providers.wikipedia import WikipediaProvider

#: Maps the CLI-facing provider name (used with --engines) to its class.
PROVIDER_REGISTRY = {
    "duckduckgo": DuckDuckGoProvider,
    "brave": BraveProvider,
    "wikipedia": WikipediaProvider,
}

#: Providers used when --engines isn't given. Brave is included even
#: though it needs an API key: if BRAVE_API_KEY isn't set it simply
#: fails gracefully like any other provider outage (see brave.py).
DEFAULT_PROVIDERS = ["duckduckgo", "brave", "wikipedia"]
