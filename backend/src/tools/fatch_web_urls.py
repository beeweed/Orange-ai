"""fatch_web_urls tool powered by Firecrawl.

Fetches one URL at a time and returns clean page content so the agent can read a
source more deeply after choosing it from web_search results.
"""
from __future__ import annotations

import json
from typing import Any, Dict
from urllib.parse import urlparse

import httpx

from src.config.settings import get_settings
from src.tools.schemas import FetchWebUrlParams, pydantic_to_openai_schema
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

FETCH_PROVIDER = "firecrawl"

FATCH_WEB_URLS_SCHEMA: Dict[str, Any] = pydantic_to_openai_schema(
    name="fatch_web_urls",
    description="Fetch and extract clean content from a URL using Firecrawl.",
    params_model=FetchWebUrlParams,
)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


async def fatch_web_urls(*, url: str, firecrawl_api_key: str | None = None) -> Dict[str, Any]:
    """Fetch one URL with Firecrawl and return clean content JSON."""
    try:
        params = FetchWebUrlParams(url=url)
        normalized_url = params.url.strip()
        if not _is_http_url(normalized_url):
            raise ValueError("url must be a valid http or https URL")
    except Exception as exc:
        return {
            "ok": False,
            "result": f"Error: invalid parameters: {exc}",
            "meta": {"tool": "fatch_web_urls", "provider": FETCH_PROVIDER},
        }

    if not firecrawl_api_key:
        return {
            "ok": False,
            "result": "Error: FIRECRAWL_API_KEY is missing. Add it in Settings before using fatch_web_urls.",
            "meta": {"tool": "fatch_web_urls", "provider": FETCH_PROVIDER, "url": normalized_url},
        }

    payload = {
        "url": normalized_url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }
    headers = {
        "Authorization": f"Bearer {firecrawl_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=120.0)) as client:
            response = await client.post(settings.firecrawl_scrape_url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "result": f"Error: failed to reach Firecrawl: {exc}",
            "meta": {"tool": "fatch_web_urls", "provider": FETCH_PROVIDER, "url": normalized_url},
        }

    if response.status_code >= 400:
        detail = response.text[:500]
        return {
            "ok": False,
            "result": f"Error: Firecrawl returned {response.status_code}: {detail}",
            "meta": {"tool": "fatch_web_urls", "provider": FETCH_PROVIDER, "url": normalized_url},
        }

    try:
        data = response.json()
    except ValueError as exc:
        return {
            "ok": False,
            "result": f"Error: Firecrawl returned invalid JSON: {exc}",
            "meta": {"tool": "fatch_web_urls", "provider": FETCH_PROVIDER, "url": normalized_url},
        }

    payload_data = data.get("data") or {}
    metadata = payload_data.get("metadata") or {}
    content = (
        payload_data.get("markdown")
        or payload_data.get("summary")
        or payload_data.get("html")
        or ""
    )
    resolved_url = metadata.get("url") or metadata.get("sourceURL") or normalized_url

    if not content:
        return {
            "ok": False,
            "result": f"Error: Firecrawl did not return extractable content for {normalized_url}.",
            "meta": {"tool": "fatch_web_urls", "provider": FETCH_PROVIDER, "url": normalized_url},
        }

    result_text = json.dumps(
        {
            "content": content,
            "url": resolved_url,
        },
        indent=2,
        ensure_ascii=False,
    )
    return {
        "ok": True,
        "result": result_text,
        "meta": {
            "tool": "fatch_web_urls",
            "provider": FETCH_PROVIDER,
            "url": resolved_url,
            "source_url": normalized_url,
            "title": metadata.get("title"),
        },
    }