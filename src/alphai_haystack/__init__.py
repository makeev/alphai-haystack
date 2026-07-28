"""Haystack components for the AlphaAI financial-news API (alphai.io)."""

from ._version import VERSION
from .fetchers import AlphaAIInsiderNewsFetcher, AlphaAINewsFetcher

__version__ = VERSION

__all__ = [
    "AlphaAIInsiderNewsFetcher",
    "AlphaAINewsFetcher",
    "__version__",
]
