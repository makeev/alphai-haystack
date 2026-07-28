from __future__ import annotations

import pytest
from alphai.models.news import RichNewsArticle
from haystack import Document

from alphai_haystack import AlphaAIInsiderNewsFetcher, AlphaAINewsFetcher
from alphai_haystack.fetchers import _to_document
from conftest import FakeClient, make_article, make_insider_event


def news_fetcher_with(articles: list[RichNewsArticle], **kwargs: object) -> AlphaAINewsFetcher:
    fetcher = AlphaAINewsFetcher(**kwargs)  # type: ignore[arg-type]
    fetcher._client = FakeClient(articles)  # type: ignore[assignment]
    return fetcher


def insider_fetcher_with(
    articles: list[RichNewsArticle], **kwargs: object
) -> AlphaAIInsiderNewsFetcher:
    fetcher = AlphaAIInsiderNewsFetcher(**kwargs)  # type: ignore[arg-type]
    fetcher._client = FakeClient(articles)  # type: ignore[assignment]
    return fetcher


def test_document_mapping() -> None:
    document = _to_document(make_article())
    assert isinstance(document, Document)
    assert document.content is not None
    assert document.content.startswith("Nvidia beats on data-center revenue")
    assert "above consensus" in document.content
    assert document.meta["uid"] == "a1b2c3d4e5f60718"
    assert document.meta["tickers"] == ["NVDA"]
    assert document.meta["category"] == "earnings"
    assert document.meta["relevance_score"] == 8
    assert document.meta["published_at"] == "2026-07-28T12:30:00+00:00"
    assert document.meta["source_domain"] == "example.com"
    assert "insider" not in document.meta


def test_document_mapping_insider_block() -> None:
    document = _to_document(make_article(insider=make_insider_event()))
    insider = document.meta["insider"]
    assert insider["side"] == "sell"
    assert insider["shares"] == "120000"
    assert insider["total_value_usd"] == "20557200.00"
    assert insider["is_10b5_1"] is True
    assert insider["insider_name"] == "Jensen Huang"
    assert insider["transaction_date"] == "2026-07-24"


def test_news_run_returns_top_k_documents(articles: list[RichNewsArticle]) -> None:
    fetcher = news_fetcher_with(articles, top_k=5)
    documents = fetcher.run()["documents"]
    assert len(documents) == 5
    assert documents[0].meta["title"] == "Article 0"


def test_news_run_passes_init_filters(articles: list[RichNewsArticle]) -> None:
    fetcher = news_fetcher_with(
        articles, symbol="NVDA", category="earnings", min_relevance=7, collapse_stories=True
    )
    fetcher.run()
    call = fetcher._client.news.iter_calls[0]  # type: ignore[union-attr]
    assert call == {
        "symbol": "NVDA",
        "category": "earnings",
        "min_relevance": 7,
        "collapse_stories": True,
        "max_items": 10,
    }


def test_news_run_overrides_beat_init(articles: list[RichNewsArticle]) -> None:
    fetcher = news_fetcher_with(articles, symbol="NVDA", min_relevance=7, top_k=10)
    fetcher.run(symbol="AMD", min_relevance=9, top_k=3)
    call = fetcher._client.news.iter_calls[0]  # type: ignore[union-attr]
    assert call["symbol"] == "AMD"
    assert call["min_relevance"] == 9
    assert call["max_items"] == 3


def test_insider_run_passes_filters(articles: list[RichNewsArticle]) -> None:
    fetcher = insider_fetcher_with(articles, symbol="NVDA", min_relevance=8, top_k=4)
    documents = fetcher.run()["documents"]
    assert len(documents) == 4
    call = fetcher._client.news.insider_calls[0]  # type: ignore[union-attr]
    assert call == {"symbol": "NVDA", "min_relevance": 8, "max_items": 4}


def test_top_k_must_be_positive() -> None:
    with pytest.raises(ValueError):
        AlphaAINewsFetcher(top_k=0)
    with pytest.raises(ValueError):
        AlphaAIInsiderNewsFetcher(top_k=-1)


def test_warm_up_uses_resolved_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[str] = []

    class RecordingClient:
        def __init__(self, api_key: str) -> None:
            created.append(api_key)

    monkeypatch.setattr("alphai_haystack.fetchers.Client", RecordingClient)
    monkeypatch.setenv("ALPHAI_API_KEY", "ak_test_123")
    fetcher = AlphaAINewsFetcher()
    fetcher.warm_up()
    fetcher.warm_up()  # second call must not create a second client
    assert created == ["ak_test_123"]
