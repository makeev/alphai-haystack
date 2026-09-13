# Changelog

## 0.1.1 — 2026-09-13

- Brand spelling in the package metadata and docs is now `AlphAI`, the form on
  the logo. Component names (`AlphaAINewsFetcher`, `AlphaAIInsiderNewsFetcher`)
  are unchanged — they are the published API.

## 0.1.0 — 2026-07-28

Initial release.

- `AlphaAINewsFetcher`: the scored news feed as Haystack Documents, with `symbol` /
  `category` / `min_relevance` / `collapse_stories` / `top_k` filters and per-run overrides.
- `AlphaAIInsiderNewsFetcher`: SEC Form 4 insider events with a structured
  `meta["insider"]` block.
- Pipeline-safe serialization (`to_dict` / `from_dict`, API key as a `Secret`
  env-var reference).
