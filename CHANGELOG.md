# Changelog

## 0.1.0 — 2026-07-28

Initial release.

- `AlphaAINewsFetcher`: the scored news feed as Haystack Documents, with `symbol` /
  `category` / `min_relevance` / `collapse_stories` / `top_k` filters and per-run overrides.
- `AlphaAIInsiderNewsFetcher`: SEC Form 4 insider events with a structured
  `meta["insider"]` block.
- Pipeline-safe serialization (`to_dict` / `from_dict`, API key as a `Secret`
  env-var reference).
