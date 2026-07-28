from __future__ import annotations

import pytest

from alphai_haystack import AlphaAIInsiderNewsFetcher, AlphaAINewsFetcher


def test_news_fetcher_to_dict_from_dict_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALPHAI_API_KEY", "ak_test_123")
    fetcher = AlphaAINewsFetcher(
        symbol="NVDA", category="earnings", min_relevance=7, collapse_stories=True, top_k=5
    )
    data = fetcher.to_dict()

    init = data["init_parameters"]
    assert init["symbol"] == "NVDA"
    assert init["category"] == "earnings"
    assert init["min_relevance"] == 7
    assert init["collapse_stories"] is True
    assert init["top_k"] == 5
    # The secret must serialize as an env-var reference, never as the raw key.
    assert init["api_key"]["type"] == "env_var"
    assert "ak_test_123" not in str(data)

    restored = AlphaAINewsFetcher.from_dict(data)
    assert restored.symbol == "NVDA"
    assert restored.top_k == 5
    assert restored.api_key.resolve_value() == "ak_test_123"


def test_insider_fetcher_to_dict_from_dict_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALPHAI_API_KEY", "ak_test_123")
    fetcher = AlphaAIInsiderNewsFetcher(symbol="AAPL", min_relevance=9, top_k=3)
    data = fetcher.to_dict()

    init = data["init_parameters"]
    assert init["symbol"] == "AAPL"
    assert init["min_relevance"] == 9
    assert init["top_k"] == 3
    assert init["api_key"]["type"] == "env_var"

    restored = AlphaAIInsiderNewsFetcher.from_dict(data)
    assert restored.symbol == "AAPL"
    assert restored.min_relevance == 9


def test_fetchers_are_pipeline_serializable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The components must survive a full Pipeline YAML round-trip."""
    from haystack import Pipeline

    monkeypatch.setenv("ALPHAI_API_KEY", "ak_test_123")
    pipeline = Pipeline()
    pipeline.add_component("news", AlphaAINewsFetcher(symbol="NVDA"))
    pipeline.add_component("insider", AlphaAIInsiderNewsFetcher(min_relevance=8))

    yaml_text = pipeline.dumps()
    assert "ak_test_123" not in yaml_text

    restored = Pipeline.loads(yaml_text)
    news = restored.get_component("news")
    assert isinstance(news, AlphaAINewsFetcher)
    assert news.symbol == "NVDA"
