import json
import re
import asyncio
from typing import AsyncGenerator, Optional, Callable

"""Autonomous coding agent.

Implements the bounded Plan -> Act -> Observe -> Reflect loop with:
- Native tool calling (tools passed via the LLM `tools` parameter; tool calls
  come from the structured API response, never parsed from text).
- Real-time, token-by-token SSE streaming of assistant content.
- Tool execution that interrupts the stream and resumes after the result.
- Full, untruncated conversation memory (the caller supplies prior history and
  the loop appends every assistant turn + tool result).
- A hard `max_iterations` cap (default 1000) and repeated-tool-call detection
  to prevent unproductive infinite loops.

The agent yields structured event dicts which the controller serialises to SSE.
"""

from typing import Any, Dict, List

from src.agent.systemprompt import SYSTEM_PROMPT
from src.schemas.chat import Credentials, Provider
from src.services.llm_service import LLMError, llm_service
from src.services.sandbox_service import SandboxError, sandbox_service
from src.tools import TOOL_SCHEMAS, execute_tool
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Agent:
    """Stateless-per-call autonomous agent.

    A single `run` invocation handles one user message: it may perform many
    internal iterations (LLM call -> tool call -> LLM call ...) until the model
    stops requesting tools or the iteration cap is reached.
    """

    def __init__(self, max_iterations: int) -> None:
        self._max_iterations = max_iterations

    @staticmethod
    def _parse_arguments(raw: str) -> Dict[str, Any]:
        """Robustly parse a tool-call argument JSON string.

        Providers occasionally emit minor artefacts; we attempt a direct parse,
        then a lenient recovery, before failing with a structured error.

        The recovery correctly handles braces, quotes, and newlines inside
        string values by tracking string boundaries, so code content like
        ``function() { return x; }`` does not corrupt the parser.
        """
        if not raw or not raw.strip():
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            candidate = Agent._try_recover_json(raw)
            if candidate is not None:
                return candidate
            raise ValueError(f"Invalid tool arguments JSON: {raw[:200]}")

    @staticmethod
    def _try_recover_json(raw: str) -> Dict[str, Any] | None:
        """Try to extract and parse a JSON object from malformed LLM output.

        Uses a state machine that respects string boundaries (handles quotes,
        escaped characters, braces inside strings, and unescaped newlines).
        Falls back to targeted extraction when JSON is irrecoverable.
        """
        start = raw.find("{")
        if start == -1:
            return None

        in_string = False
        escape = False
        depth = 0

        for end in range(start, len(raw)):
            ch = raw[end]

            # Track string boundaries to ignore braces inside strings
            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue

            if not in_string:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = raw[start:end + 1]
                        # First attempt: direct parse
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            pass
                        # Second attempt: replace unescaped newlines inside
                        # string values with \\n to make the JSON valid.
                        try:
                            fixed = Agent._fix_unescaped_newlines(candidate)
                            return json.loads(fixed)
                        except (json.JSONDecodeError, ValueError):
                            pass
                        # Final fallback: try targeted extraction of known
                        # tool parameters from the raw text.
                        try:
                            return Agent._extract_params_fallback(candidate)
                        except (json.JSONDecodeError, ValueError, TypeError):
                            return None

        return None

    @staticmethod
    def _fix_unescaped_newlines(s: str) -> str:
        """Replace literal newline characters inside JSON string values with \\n."""
        result = []
        in_str = False
        esc = False
        for ch in s:
            if esc:
                result.append(ch)
                esc = False
                continue
            if ch == "\\" and in_str:
                result.append(ch)
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                result.append(ch)
                continue
            if in_str and ch in "\n\r":
                result.append("\\n" if ch == "\n" else "\\r")
                continue
            result.append(ch)
        return "".join(result)

    @staticmethod
    def _extract_params_fallback(raw: str) -> Dict[str, Any]:
        """Last-resort extraction of tool parameters from malformed JSON.

        Uses targeted string operations to find known parameter keys and
        their string values, handling unescaped quotes within values.
        """
        result: Dict[str, Any] = {}
        known_keys = ["file_path", "old_string", "new_string", "content", "replace_all"]

        for key in known_keys:
            pattern = f'"{key}"\\s*:\\s*"'
            match = re.search(pattern, raw)
            if not match:
                continue

            val_start = match.end()
            # Find the end of the string value, handling escaped quotes
            val_parts: list[str] = []
            i = val_start
            while i < len(raw):
                if raw[i] == "\\" and i + 1 < len(raw):
                    val_parts.append(raw[i])
                    val_parts.append(raw[i + 1])
                    i += 2
                elif raw[i] == '"':
                    # End of string value
                    break
                else:
                    val_parts.append(raw[i])
                    i += 1

            val = "".join(val_parts)

            if key == "replace_all":
                # Try to find a boolean value instead of string
                bool_match = re.search(f'"{key}"\\s*:\\s*(true|false)', raw)
                if bool_match:
                    result[key] = bool_match.group(1) == "true"
                else:
                    result[key] = val.lower() == "true" if val else False
            else:
                result[key] = val

        if not result:
            raise ValueError("could not extract parameters")

        return result

    @staticmethod
    def _signature(name: str, arguments: Dict[str, Any]) -> str:
        """Stable signature of a tool call for repeat detection."""
        try:
            return f"{name}:{json.dumps(arguments, sort_keys=True)}"
        except TypeError:
            return f"{name}:{str(arguments)}"

    async def run(
        self,
        *,
        credentials: Credentials,
        history: List[Dict[str, Any]],
        user_message: str,
        sandbox_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Run one autonomous turn, yielding structured agent events.

        Event kinds yielded (consumed by the controller -> SSE):
          {"type": "iteration", "current": int, "max": int}
          {"type": "thinking"}
          {"type": "token", "text": str}
          {"type": "tool_call", "id", "name", "arguments", "display"}
          {"type": "tool_result", "id", "name", "ok", "result", "meta"}
          {"type": "message_done"}            # end of one assistant message
          {"type": "error", "message": str}
          {"type": "done", "iterations": int} # end of the whole turn
        """
        provider: Provider = credentials.provider

        # Build the working message list: system + full prior history + new user.
        messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        recent_signatures: List[str] = []
        tool_execution_context: Dict[str, Any] = {"read_files": set()}
        iteration = 0

        while iteration < self._max_iterations:
            iteration += 1
            yield {"type": "iteration", "current": iteration, "max": self._max_iterations}
            yield {"type": "thinking"}

            assistant_text_parts: List[str] = []
            tool_calls: List[Dict[str, Any]] = []
            finish_reason = "stop"
            started_content = False

            # ---- Stream the model response token-by-token ---- #
            try:
                async for delta in llm_service.stream_chat(
                    provider=provider,
                    api_key=credentials.api_key,
                    model=credentials.model,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                ):
                    kind = delta.get("kind")
                    if kind == "content":
                        text = delta["text"]
                        assistant_text_parts.append(text)
                        if not started_content:
                            started_content = True
                            yield {"type": "content_start"}
                        # Token-level streaming to the client.
                        yield {"type": "token", "text": text}
                        # Yield control so each token is flushed smoothly.
                        await asyncio.sleep(0)
                    elif kind == "tool_calls":
                        tool_calls = delta["tool_calls"]
                    elif kind == "finish":
                        finish_reason = delta.get("reason") or "stop"
            except LLMError as exc:
                logger.error("LLM error on iteration %d: %s", iteration, exc)
                yield {"type": "error", "message": str(exc)}
                yield {"type": "done", "iterations": iteration}
                return

            assistant_text = "".join(assistant_text_parts)

            # Record the assistant message in memory (content + any tool calls).
            assistant_msg: Dict[str, Any] = {"role": "assistant"}
            assistant_msg["content"] = assistant_text or None
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            yield {"type": "message_done", "content": assistant_text}

            # ---- No tool calls => the turn is complete ---- #
            if not tool_calls:
                yield {"type": "done", "iterations": iteration}
                return

            # ---- Execute each requested tool call sequentially ---- #
            stop_after_tools = False
            for call in tool_calls:
                call_id = call.get("id") or "call_0"
                fn = call.get("function") or {}
                name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")

                try:
                    arguments = self._parse_arguments(raw_args)
                except ValueError as exc:
                    # Feed a structured error back so the model can self-correct.
                    err = f"Error: {exc}"
                    yield {
                        "type": "tool_call",
                        "id": call_id,
                        "name": name,
                        "arguments": {},
                        "display": self._display_label(name, {}),
                    }
                    yield {
                        "type": "tool_result",
                        "id": call_id,
                        "name": name,
                        "ok": False,
                        "result": err,
                        "meta": {"tool": name},
                    }
                    messages.append(
                        {"role": "tool", "tool_call_id": call_id, "content": err}
                    )
                    continue

                # Repeated-tool-call detection (poka-yoke against infinite loops).
                signature = self._signature(name, arguments)
                recent_signatures.append(signature)
                if recent_signatures.count(signature) >= 3:
                    note = (
                        f"Error: tool '{name}' was called repeatedly with identical "
                        f"arguments. Stopping to avoid an unproductive loop. "
                        f"Reassess the task and either fix the approach or finish."
                    )
                    yield {
                        "type": "tool_result",
                        "id": call_id,
                        "name": name,
                        "ok": False,
                        "result": note,
                        "meta": {"tool": name, "repeated": True},
                    }
                    messages.append(
                        {"role": "tool", "tool_call_id": call_id, "content": note}
                    )
                    stop_after_tools = True
                    continue

                # Announce the tool call (chip) before executing.
                yield {
                    "type": "tool_call",
                    "id": call_id,
                    "name": name,
                    "arguments": arguments,
                    "display": self._display_label(name, arguments),
                }

                # Execute the tool against the sandbox.
                try:
                    result = await execute_tool(
                        name,
                        arguments,
                        sandbox_id=sandbox_id,
                        e2b_api_key=credentials.e2b_api_key,
                        execution_context=tool_execution_context,
                    )
                except SandboxError as exc:
                    result = {
                        "ok": False,
                        "result": f"Sandbox error: {exc}",
                        "meta": {"tool": name},
                    }
                except Exception as exc:  # noqa: BLE001 - never let a tool crash the loop
                    logger.exception("Unexpected tool error")
                    result = {
                        "ok": False,
                        "result": f"Unexpected error executing {name}: {exc}",
                        "meta": {"tool": name},
                    }

                yield {
                    "type": "tool_result",
                    "id": call_id,
                    "name": name,
                    "ok": result.get("ok", False),
                    "result": result.get("result", ""),
                    "meta": result.get("meta", {}),
                }

                # Append the tool result to memory for the next LLM call.
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": result.get("result", ""),
                    }
                )

            if stop_after_tools:
                yield {"type": "done", "iterations": iteration}
                return

            # Loop continues: the model will observe tool results and proceed.

        # Iteration cap reached -> return best progress so far.
        yield {
            "type": "error",
            "message": f"Reached maximum iteration limit ({self._max_iterations}).",
        }
        yield {"type": "done", "iterations": iteration}

    @staticmethod
    def _display_label(name: str, arguments: Dict[str, Any]) -> str:
        """Human-friendly chip label, e.g. 'create: /path' or 'read: /path'."""
        path = arguments.get("file_path", "")
        if name == "file_write":
            return f"create: {path}" if path else "create"
        if name == "file_read":
            return f"read: {path}" if path else "read"
        if name == "file_editor":
            return f"edit: {path}" if path else "edit"
        return name
