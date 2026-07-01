"""web_search tool powered by Tavily.

Searches the live web for recent or unknown information and returns a compact,
LLM-friendly JSON array of results containing only title, url, and Description.
"""
from __future__ import annotations

import json
from typing import Any, Dict

import httpx

from src.config.settings import get_settings
from src.tools.schemas import WebSearchParams, pydantic_to_openai_schema
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

MAX_SEARCH_RESULTS = 15
SEARCH_PROVIDER = "tavily"

WEB_SEARCH_SCHEMA: Dict[str, Any] = pydantic_to_openai_schema(
    name="web_search",
    description="Search the web using Tavily for up-to-date information, news, and general knowledge.",
    params_model=WebSearchParams,
)


async def web_search(*, query: str, tavily_api_key: str | None = None) -> Dict[str, Any]:
    """Search the web with Tavily and return compact JSON search results."""
    try:
        params = WebSearchParams(query=query)
        normalized_query = params.query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty")
    except Exception as exc:
        return {
            "ok": False,
            "result": f"Error: invalid parameters: {exc}",
            "meta": {"tool": "web_search", "provider": SEARCH_PROVIDER},
        }

    if not tavily_api_key:
        return {
            "ok": False,
            "result": "Error: TAVILY_API_KEY is missing. Add it in Settings before using web_search.",
            "meta": {"tool": "web_search", "provider": SEARCH_PROVIDER},
        }

    payload = {
        "query": normalized_query,
        "max_results": min(settings.max_search_results, MAX_SEARCH_RESULTS),
        "search_depth": "basic",
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
    }
    headers = {
        "Authorization": f"Bearer {tavily_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=60.0)) as client:
            response = await client.post(settings.tavily_search_url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "result": f"Error: failed to reach Tavily: {exc}",
            "meta": {"tool": "web_search", "provider": SEARCH_PROVIDER, "query": normalized_query},
        }

    if response.status_code >= 400:
        detail = response.text[:500]
        return {
            "ok": False,
            "result": f"Error: Tavily returned {response.status_code}: {detail}",
            "meta": {"tool": "web_search", "provider": SEARCH_PROVIDER, "query": normalized_query},
        }

    try:
        data = response.json()
    except ValueError as exc:
        return {
            "ok": False,
            "result": f"Error: Tavily returned invalid JSON: {exc}",
            "meta": {"tool": "web_search", "provider": SEARCH_PROVIDER, "query": normalized_query},
        }

    raw_results = data.get("results") or []
    results = []
    for item in raw_results[:MAX_SEARCH_RESULTS]:
        url = (item.get("url") or "").strip()
        title = (item.get("title") or url or "Untitled result").strip()
        description = (
            item.get("content")
            or item.get("description")
            or item.get("snippet")
            or ""
        )
        results.append(
            {
                "title": title,
                "url": url,
                "Description": description.strip(),
            }
        )

    result_text = json.dumps(results, indent=2, ensure_ascii=False)
    return {
        "ok": True,
        "result": result_text,
        "meta": {
            "tool": "web_search",
            "provider": SEARCH_PROVIDER,
            "query": normalized_query,
            "count": len(results),
            "max_results": MAX_SEARCH_RESULTS,
        },
    }