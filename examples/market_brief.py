"""Market brief for one ticker: AlphaAI scored news -> prompt -> LLM.

Needs ALPHAI_API_KEY (free at https://alphai.io/developers) and OPENAI_API_KEY.

    python examples/market_brief.py NVDA
"""

from __future__ import annotations

import sys

from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator

from alphai_haystack import AlphaAINewsFetcher

TEMPLATE = """Summarize what moved {{ symbol }} recently, using only these articles.
Lead with the single most market-relevant item.

{% for doc in documents %}
- {{ doc.content }} (relevance {{ doc.meta.relevance_score }}/10, {{ doc.meta.category }})
{% endfor %}
"""


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "NVDA"

    pipeline = Pipeline()
    pipeline.add_component("news", AlphaAINewsFetcher(min_relevance=6, collapse_stories=True))
    pipeline.add_component("prompt", PromptBuilder(template=TEMPLATE))
    pipeline.add_component("llm", OpenAIGenerator(model="gpt-4o-mini"))
    pipeline.connect("news.documents", "prompt.documents")
    pipeline.connect("prompt", "llm")

    result = pipeline.run({"news": {"symbol": symbol}, "prompt": {"symbol": symbol}})
    print(result["llm"]["replies"][0])


if __name__ == "__main__":
    main()
