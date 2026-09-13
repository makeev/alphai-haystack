"""Haystack components that turn AlphAI's scored news feed into Documents.

Every article on the feed already carries an AI enrichment layer (per-ticker
impact analysis, a category, a 1-10 relevance score), so the components here
do no scoring of their own — they fetch, filter, and map articles into
:class:`haystack.Document` objects with the enrichment exposed as metadata.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from alphai import Client
from alphai.models import RichNewsArticle
from haystack import Document, component, default_from_dict, default_to_dict
from haystack.utils import Secret, deserialize_secrets_inplace

DEFAULT_TOP_K = 10


def _plain(value: object) -> object:
    """Convert SDK field values into JSON-friendly meta values."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _category_str(category: object) -> str:
    return str(getattr(category, "value", category))


def _to_document(article: RichNewsArticle) -> Document:
    original = article.original
    enrichment = article.enrichment
    parts = [original.title.strip(), original.summary.strip()]
    content = "\n\n".join(part for part in parts if part)
    meta: dict[str, Any] = {
        "uid": original.uid,
        "url": original.url,
        "title": original.title,
        "source": original.source,
        "source_domain": original.source_domain,
        "published_at": _plain(original.time_published),
        "tickers": list(enrichment.tickers),
        "category": _category_str(enrichment.category),
        "relevance_score": enrichment.relevance_score,
    }
    if article.sources_count is not None:
        meta["sources_count"] = article.sources_count
    if article.insider is not None:
        event = article.insider
        meta["insider"] = {
            "side": event.side,
            "transaction_code": event.transaction_code,
            "shares": _plain(event.shares),
            "avg_price_usd": _plain(event.avg_price_usd),
            "total_value_usd": _plain(event.total_value_usd),
            "is_10b5_1": event.is_10b5_1,
            "insider_name": event.insider_name,
            "insider_title": event.insider_title,
            "is_officer": event.is_officer,
            "is_director": event.is_director,
            "is_ten_percent_owner": event.is_ten_percent_owner,
            "transaction_date": _plain(event.transaction_date),
        }
    return Document(content=content, meta=meta)


@component
class AlphaAINewsFetcher:
    """Fetches AI-scored financial news from AlphAI as Haystack Documents.

    Each Document's ``content`` is the article title plus summary; ``meta``
    carries the enrichment (tickers, category, 1-10 ``relevance_score``,
    source, url, publish time). Filters set in ``__init__`` are defaults and
    can be overridden per ``run()`` call.

    Requires an AlphAI API key (free tier available, no card) — see
    https://alphai.io/developers. The key is read from the ``ALPHAI_API_KEY``
    environment variable by default.

    ```python
    from alphai_haystack import AlphaAINewsFetcher

    fetcher = AlphaAINewsFetcher(symbol="NVDA", min_relevance=7)
    documents = fetcher.run()["documents"]
    ```
    """

    def __init__(
        self,
        api_key: Secret = Secret.from_env_var("ALPHAI_API_KEY"),
        symbol: str | None = None,
        category: str | None = None,
        min_relevance: int | None = None,
        collapse_stories: bool = False,
        top_k: int = DEFAULT_TOP_K,
    ) -> None:
        """
        :param api_key: AlphAI API key. Defaults to the ``ALPHAI_API_KEY`` env var.
        :param symbol: Only articles tagged with this ticker (e.g. ``"NVDA"``).
        :param category: Only articles in this category (e.g. ``"earnings"``,
            ``"mergers_acquisitions"``, ``"insider"``).
        :param min_relevance: Only articles scored at or above this 1-10 floor.
        :param collapse_stories: Collapse same-story coverage into one item.
        :param top_k: Maximum number of Documents to return per run.
        """
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        self.api_key = api_key
        self.symbol = symbol
        self.category = category
        self.min_relevance = min_relevance
        self.collapse_stories = collapse_stories
        self.top_k = top_k
        self._client: Client | None = None

    def warm_up(self) -> None:
        """Create the underlying API client once."""
        if self._client is None:
            self._client = Client(api_key=self.api_key.resolve_value())

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
            symbol=self.symbol,
            category=self.category,
            min_relevance=self.min_relevance,
            collapse_stories=self.collapse_stories,
            top_k=self.top_k,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlphaAINewsFetcher:
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        result: AlphaAINewsFetcher = default_from_dict(cls, data)
        return result

    @component.output_types(documents=list[Document])
    def run(
        self,
        symbol: str | None = None,
        category: str | None = None,
        min_relevance: int | None = None,
        top_k: int | None = None,
    ) -> dict[str, list[Document]]:
        """Fetch the newest matching articles.

        :param symbol: Overrides the ticker filter set in ``__init__``.
        :param category: Overrides the category filter set in ``__init__``.
        :param min_relevance: Overrides the relevance floor set in ``__init__``.
        :param top_k: Overrides the maximum number of Documents.
        :returns: ``{"documents": [...]}`` — newest first.
        """
        self.warm_up()
        assert self._client is not None
        articles = self._client.news.iter(
            symbol=symbol if symbol is not None else self.symbol,
            category=category if category is not None else self.category,
            min_relevance=min_relevance if min_relevance is not None else self.min_relevance,
            collapse_stories=self.collapse_stories,
            max_items=top_k if top_k is not None else self.top_k,
        )
        return {"documents": [_to_document(article) for article in articles]}


@component
class AlphaAIInsiderNewsFetcher:
    """Fetches SEC Form 4 insider-trading events from AlphAI as Documents.

    Every item is one insider event (a filing's grouped buy/sell transactions)
    with a structured ``meta["insider"]`` block: side, shares, average price,
    total value, who traded, and whether it was a pre-planned 10b5-1 sale.
    Relevance scores on this feed are deterministic from the event's summed
    value, so ``min_relevance`` works as an "only large trades" dial.

    ```python
    from alphai_haystack import AlphaAIInsiderNewsFetcher

    fetcher = AlphaAIInsiderNewsFetcher(min_relevance=7)
    documents = fetcher.run()["documents"]
    ```
    """

    def __init__(
        self,
        api_key: Secret = Secret.from_env_var("ALPHAI_API_KEY"),
        symbol: str | None = None,
        min_relevance: int | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> None:
        """
        :param api_key: AlphAI API key. Defaults to the ``ALPHAI_API_KEY`` env var.
        :param symbol: Only events for this ticker (share-class siblings included).
        :param min_relevance: 1-10 floor; higher means larger trades only.
        :param top_k: Maximum number of Documents to return per run.
        """
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        self.api_key = api_key
        self.symbol = symbol
        self.min_relevance = min_relevance
        self.top_k = top_k
        self._client: Client | None = None

    def warm_up(self) -> None:
        """Create the underlying API client once."""
        if self._client is None:
            self._client = Client(api_key=self.api_key.resolve_value())

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
            symbol=self.symbol,
            min_relevance=self.min_relevance,
            top_k=self.top_k,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlphaAIInsiderNewsFetcher:
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        result: AlphaAIInsiderNewsFetcher = default_from_dict(cls, data)
        return result

    @component.output_types(documents=list[Document])
    def run(
        self,
        symbol: str | None = None,
        min_relevance: int | None = None,
        top_k: int | None = None,
    ) -> dict[str, list[Document]]:
        """Fetch the newest matching insider events.

        :param symbol: Overrides the ticker filter set in ``__init__``.
        :param min_relevance: Overrides the relevance floor set in ``__init__``.
        :param top_k: Overrides the maximum number of Documents.
        :returns: ``{"documents": [...]}`` — newest first.
        """
        self.warm_up()
        assert self._client is not None
        articles = self._client.news.insider_iter(
            symbol=symbol if symbol is not None else self.symbol,
            min_relevance=min_relevance if min_relevance is not None else self.min_relevance,
            max_items=top_k if top_k is not None else self.top_k,
        )
        return {"documents": [_to_document(article) for article in articles]}
