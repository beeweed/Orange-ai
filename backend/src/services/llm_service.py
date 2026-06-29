"""LLM provider service.

Provides a unified, provider-agnostic async interface over OpenAI-compatible
chat-completion APIs (OpenRouter and NVIDIA NIM today; trivially extensible).

Responsibilities:
- List available models for a provider (`list_models`).
- Stream a chat completion with native tool calling, yielding granular events
  the agent loop consumes: content tokens and assembled tool calls.

Both providers speak the OpenAI wire protocol, so a single client implementation
parameterised by base URL + headers covers them. New providers can be added by
extending `_provider_config` only.
"""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import httpx

from src.config.settings import get_settings
from src.schemas.chat import ModelInfo, Provider
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LLMError(Exception):
    """Raised on provider communication or protocol errors."""


class LLMService:
    """Unified client for OpenAI-compatible LLM providers."""

    def __init__(self) -> None:
        self._settings = get_settings()

    # ------------------------------------------------------------------ #
    # Provider configuration                                             #
    # ------------------------------------------------------------------ #
    def _provider_config(self, provider: Provider, api_key: str) -> Tuple[str, Dict[str, str]]:
        """Return (base_url, headers) for a provider. Extend here for new ones."""
        if provider == Provider.OPENROUTER:
            return (
                self._settings.openrouter_base_url,
                {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self._settings.openrouter_referer,
                    "X-Title": self._settings.openrouter_title,
                },
            )
        if provider == Provider.NVIDIA:
            return (
                self._settings.nvidia_base_url,
                {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
        raise LLMError(f"Unsupported provider: {provider}")

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self._settings.http_connect_timeout,
            read=self._settings.http_read_timeout,
            write=self._settings.http_read_timeout,
            pool=self._settings.http_connect_timeout,
        )

    # ------------------------------------------------------------------ #
    # Model listing                                                      #
    # ------------------------------------------------------------------ #
    async def list_models(self, provider: Provider, api_key: str) -> List[ModelInfo]:
        """Fetch all available models for the provider."""
        base_url, headers = self._provider_config(provider, api_key)
        url = f"{base_url}/models"

        try:
            async with httpx.AsyncClient(timeout=self._timeout()) as client:
                resp = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            raise LLMError(f"Failed to reach provider: {exc}") from exc

        if resp.status_code == 401:
            raise LLMError("Invalid API key (unauthorized).")
        if resp.status_code >= 400:
            raise LLMError(f"Provider returned {resp.status_code}: {resp.text[:300]}")

        payload = resp.json()
        raw_models = payload.get("data", payload.get("models", []))
        models: List[ModelInfo] = []
        for m in raw_models:
            model_id = m.get("id") or m.get("name")
            if not model_id:
                continue
            name = m.get("name") or model_id
            models.append(
                ModelInfo(
                    id=model_id,
                    name=name,
                    description=(m.get("description") or None),
                    context_length=(
                        m.get("context_length")
                        or (m.get("top_provider") or {}).get("context_length")
                    ),
                )
            )
        models.sort(key=lambda x: x.id.lower())
        logger.info("Fetched %d models from %s", len(models), provider.value)
        return models

    # ------------------------------------------------------------------ #
    # Streaming chat completion with native tool calling                 #
    # ------------------------------------------------------------------ #
    async def stream_chat(
        self,
        *,
        provider: Provider,
        api_key: str,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a chat completion, yielding structured deltas.

        Yields dicts of the form:
          {"kind": "content", "text": "..."}                 # a content token
          {"kind": "tool_calls", "tool_calls": [...]}        # assembled at end
          {"kind": "finish", "reason": "stop|tool_calls"}    # terminal

        Tool-call fragments arrive incrementally across SSE chunks; this method
        reassembles them into complete tool calls (id, name, full argument JSON)
        before emitting a single `tool_calls` event.
        """
        base_url, headers = self._provider_config(provider, api_key)
        url = f"{base_url}/chat/completions"

        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        # Accumulator for streamed tool calls keyed by their index.
        tool_acc: Dict[int, Dict[str, Any]] = {}
        finish_reason: Optional[str] = None

        try:
            async with httpx.AsyncClient(timeout=self._timeout()) as client:
                async with client.stream("POST", url, headers=headers, json=body) as resp:
                    if resp.status_code >= 400:
                        err_body = (await resp.aread()).decode("utf-8", "replace")
                        raise LLMError(f"Provider error {resp.status_code}: {err_body[:500]}")

                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue

                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        choice = choices[0]
                        delta = choice.get("delta") or {}

                        # Content tokens -> stream immediately.
                        content_piece = delta.get("content")
                        if content_piece:
                            yield {"kind": "content", "text": content_piece}

                        # Tool-call fragments -> accumulate by index.
                        for tc in delta.get("tool_calls") or []:
                            idx = tc.get("index", 0)
                            slot = tool_acc.setdefault(
                                idx,
                                {"id": None, "name": None, "arguments": ""},
                            )
                            if tc.get("id"):
                                slot["id"] = tc["id"]
                            fn = tc.get("function") or {}
                            if fn.get("name"):
                                slot["name"] = fn["name"]
                            if fn.get("arguments"):
                                slot["arguments"] += fn["arguments"]

                        if choice.get("finish_reason"):
                            finish_reason = choice["finish_reason"]

        except httpx.HTTPError as exc:
            raise LLMError(f"Streaming connection failed: {exc}") from exc

        # Emit assembled tool calls (if any) once the stream completes.
        if tool_acc:
            assembled = []
            for idx in sorted(tool_acc.keys()):
                slot = tool_acc[idx]
                if not slot.get("name"):
                    continue
                assembled.append(
                    {
                        "id": slot["id"] or f"call_{idx}",
                        "type": "function",
                        "function": {
                            "name": slot["name"],
                            "arguments": slot["arguments"] or "{}",
                        },
                    }
                )
            if assembled:
                yield {"kind": "tool_calls", "tool_calls": assembled}
                finish_reason = finish_reason or "tool_calls"

        yield {"kind": "finish", "reason": finish_reason or "stop"}


# Module-level singleton.
llm_service = LLMService()
