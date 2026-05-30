"""Deterministic web search skeleton for candidate source discovery."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from urllib.parse import quote_plus

from backend.config import Settings

SearchProvider = Callable[..., Awaitable[list[dict[str, Any]]]]


@dataclass(frozen=True, slots=True)
class SearchResultItem:
    """One normalized web search candidate."""

    title: str
    url: str
    snippet: str
    source_type: str

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source_type": self.source_type,
        }


@dataclass(frozen=True, slots=True)
class SearchResults:
    """Normalized output for web_search."""

    query: str
    results: list[SearchResultItem]
    new_result_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "results": [result.to_dict() for result in self.results],
            "new_result_count": self.new_result_count,
        }


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query).strip()


def _source_type_for_url(url: str) -> str:
    lowered = url.lower()
    if ".gov" in lowered or "federalregister.gov" in lowered:
        return "gov"
    if ".edu" in lowered or "arxiv.org" in lowered:
        return "academic"
    if "github.com" in lowered:
        return "github"
    if "sam.gov" in lowered or "usaspending.gov" in lowered:
        return "procurement"
    return "web"


def _default_results(query: str, num_results: int) -> list[dict[str, Any]]:
    encoded_query = quote_plus(query.lower())
    candidates = [
        {
            "title": f"Government source for {query}",
            "url": f"https://search.usa.gov/search?query={encoded_query}",
            "snippet": f"Government search result candidate for {query}.",
            "source_type": "gov",
        },
        {
            "title": f"Federal Register source for {query}",
            "url": f"https://www.federalregister.gov/documents/search?conditions%5Bterm%5D={encoded_query}",
            "snippet": f"Federal Register candidate source for {query}.",
            "source_type": "gov",
        },
        {
            "title": f"Research source for {query}",
            "url": f"https://arxiv.org/search/?query={encoded_query}&searchtype=all",
            "snippet": f"Academic and technical candidate source for {query}.",
            "source_type": "academic",
        },
        {
            "title": f"GitHub source for {query}",
            "url": f"https://github.com/search?q={encoded_query}",
            "snippet": f"Open-source project candidate source for {query}.",
            "source_type": "github",
        },
        {
            "title": f"General web source for {query}",
            "url": f"https://www.google.com/search?q={encoded_query}",
            "snippet": f"General web candidate source for {query}.",
            "source_type": "web",
        },
    ]
    return candidates[:num_results]


def _normalize_item(raw_item: dict[str, Any], *, query: str) -> SearchResultItem | None:
    url = str(raw_item.get("url", "")).strip()
    if not url.startswith(("http://", "https://")):
        return None
    title = str(raw_item.get("title") or url).strip()
    snippet = str(raw_item.get("snippet") or f"Candidate source for {query}.").strip()
    source_type = str(raw_item.get("source_type") or _source_type_for_url(url)).strip()
    return SearchResultItem(title=title, url=url, snippet=snippet, source_type=source_type)


async def web_search(
    settings: Settings,
    *,
    query: str,
    num_results: int = 5,
    existing_urls: set[str] | None = None,
    provider: SearchProvider | None = None,
) -> SearchResults:
    """Return normalized candidate source results for a research query."""
    del settings
    normalized_query = _normalize_query(query)
    if not normalized_query:
        raise ValueError("empty_query")
    if num_results < 1 or num_results > 10:
        raise ValueError("invalid_num_results")

    raw_results = await provider(query=normalized_query, num_results=num_results) if provider else _default_results(
        normalized_query,
        num_results,
    )
    seen_urls = set(existing_urls or set())
    normalized_results: list[SearchResultItem] = []
    for raw_item in raw_results:
        item = _normalize_item(raw_item, query=normalized_query)
        if item is None or item.url in seen_urls:
            continue
        seen_urls.add(item.url)
        normalized_results.append(item)
        if len(normalized_results) >= num_results:
            break

    return SearchResults(
        query=normalized_query,
        results=normalized_results,
        new_result_count=len(normalized_results),
    )
