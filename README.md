# alphai-haystack

[![PyPI](https://img.shields.io/pypi/v/alphai-haystack)](https://pypi.org/project/alphai-haystack/)
[![CI](https://github.com/makeev/alphai-haystack/actions/workflows/ci.yml/badge.svg)](https://github.com/makeev/alphai-haystack/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Haystack](https://haystack.deepset.ai) components for [AlphaAI](https://alphai.io) — AI-scored
financial news and SEC Form 4 insider events, delivered as Haystack `Document` objects.

Every article on the AlphaAI feed is enriched at ingest: per-ticker impact analysis, a category,
and a 1-10 relevance score. SEC Form 4 filings become structured insider events about 6 minutes
after they hit EDGAR. These components fetch that feed so your pipelines and agents can reason
over pre-scored market news instead of raw headlines.

## Components

- **`AlphaAINewsFetcher`** — the main news feed. Filter by ticker, category, and a relevance
  floor; optionally collapse same-story coverage into one item.
- **`AlphaAIInsiderNewsFetcher`** — SEC Form 4 insider events with a structured
  `meta["insider"]` block: side, shares, average price, total value, who traded, and whether it
  was a pre-planned 10b5-1 sale.

## Installation

```bash
pip install alphai-haystack
```

## API key

Get a free key at [alphai.io/developers](https://alphai.io/developers) (free tier: 20 requests
per minute, 100 per day, no card). The components read it from the `ALPHAI_API_KEY` environment
variable by default:

```bash
export ALPHAI_API_KEY="ak_..."
```

## Usage

### Standalone

```python
from alphai_haystack import AlphaAINewsFetcher

fetcher = AlphaAINewsFetcher(symbol="NVDA", min_relevance=7)
documents = fetcher.run()["documents"]

for doc in documents:
    print(doc.meta["relevance_score"], doc.meta["title"])
```

### Insider events

```python
from alphai_haystack import AlphaAIInsiderNewsFetcher

fetcher = AlphaAIInsiderNewsFetcher(min_relevance=7)  # higher floor = larger trades
for doc in fetcher.run()["documents"]:
    insider = doc.meta["insider"]
    print(insider["insider_name"], insider["side"], insider["total_value_usd"], doc.meta["tickers"])
```

### In a pipeline

A minimal market-brief pipeline: fetch scored news for a ticker, hand it to an LLM.

```python
from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator

from alphai_haystack import AlphaAINewsFetcher

template = """Summarize what moved {{ symbol }} today, using only these articles:
{% for doc in documents %}
- {{ doc.content }} (relevance {{ doc.meta.relevance_score }}/10)
{% endfor %}
"""

pipeline = Pipeline()
pipeline.add_component("news", AlphaAINewsFetcher(min_relevance=6, collapse_stories=True))
pipeline.add_component("prompt", PromptBuilder(template=template))
pipeline.add_component("llm", OpenAIGenerator(model="gpt-4o-mini"))
pipeline.connect("news.documents", "prompt.documents")
pipeline.connect("prompt", "llm")

result = pipeline.run({"news": {"symbol": "NVDA"}, "prompt": {"symbol": "NVDA"}})
print(result["llm"]["replies"][0])
```

Both components implement `to_dict`/`from_dict`, so pipelines serialize to YAML and back; the
API key is stored as an environment-variable reference, never as the raw value.

## Document shape

`content` is the article title plus summary. `meta` carries:

| Key | Type | Notes |
|---|---|---|
| `uid` | str | Stable article id (use with the AlphaAI article endpoint) |
| `url` | str | Original article URL |
| `title`, `source`, `source_domain` | str | |
| `published_at` | str | ISO 8601 |
| `tickers` | list[str] | Tickers the article affects |
| `category` | str | One of 14 categories (`earnings`, `insider`, `crypto`, ...) |
| `relevance_score` | int | 1-10, assigned at ingest |
| `sources_count` | int | Only when `collapse_stories=True` |
| `insider` | dict | Insider feed only: side, shares, avg price, total value, who |

## Run parameters

`run()` accepts per-call overrides for the filters set in `__init__`: `symbol`, `category`
(news fetcher only), `min_relevance`, and `top_k`.

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
mypy src/alphai_haystack
pytest
```

Tests run fully offline against a fake client.

## Links

- [AlphaAI developer docs](https://alphai.io/developers)
- [OpenAPI schema](https://api.alphai.io/api/schema/)
- [Python SDK (`alphai-sdk`)](https://github.com/makeev/alphai-sdk) — this package is a thin
  Haystack layer over it
- [MCP server](https://alphai.io/mcp) — the same feed for MCP-speaking agents

## License

MIT
