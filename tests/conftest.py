from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from alphai.models.news import (
    EnrichedArticle,
    InsiderEvent,
    OriginalArticle,
    RichNewsArticle,
)


def make_article(
    uid: str = "a1b2c3d4e5f60718",
    title: str = "Nvidia beats on data-center revenue",
    summary: str = "Q2 revenue came in above consensus, driven by data-center demand.",
    tickers: list[str] | None = None,
    relevance_score: int = 8,
    category: str = "earnings",
    insider: InsiderEvent | None = None,
    sources_count: int | None = None,
) -> RichNewsArticle:
    return RichNewsArticle(
        original=OriginalArticle(
            uid=uid,
            title=title,
            url=f"https://example.com/{uid}",
            time_published=datetime(2026, 7, 28, 12, 30, tzinfo=timezone.utc),
            summary=summary,
            source="Example Wire",
            source_domain="example.com",
        ),
        enrichment=EnrichedArticle(
            category=category,
            tickers=tickers if tickers is not None else ["NVDA"],
            relevance_score=relevance_score,
        ),
        insider=insider,
        sources_count=sources_count,
    )


def make_insider_event() -> InsiderEvent:
    return InsiderEvent(
        side="sell",
        transaction_code="S",
        shares=Decimal("120000"),
        avg_price_usd=Decimal("171.31"),
        total_value_usd=Decimal("20557200.00"),
        is_10b5_1=True,
        insider_name="Jensen Huang",
        insider_title="CEO",
        is_officer=True,
        transaction_date=date(2026, 7, 24),
    )


class FakeNewsResource:
    """Records call kwargs and yields canned articles."""

    def __init__(self, articles: list[RichNewsArticle]) -> None:
        self.articles = articles
        self.iter_calls: list[dict[str, Any]] = []
        self.insider_calls: list[dict[str, Any]] = []

    def iter(self, **kwargs: Any) -> Iterator[RichNewsArticle]:
        self.iter_calls.append(kwargs)
        max_items = kwargs.get("max_items")
        yield from self.articles[:max_items]

    def insider_iter(self, **kwargs: Any) -> Iterator[RichNewsArticle]:
        self.insider_calls.append(kwargs)
        max_items = kwargs.get("max_items")
        yield from self.articles[:max_items]


class FakeClient:
    def __init__(self, articles: list[RichNewsArticle]) -> None:
        self.news = FakeNewsResource(articles)


@pytest.fixture()
def articles() -> list[RichNewsArticle]:
    return [make_article(uid=f"uid{i:013d}", title=f"Article {i}") for i in range(25)]
