import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from agents import FunctionTool, ModelBehaviorError, function_tool
from agents.tool_context import ToolContext

from app.config import Settings
from app.core.context import RunContext
from app.core.contracts import ToolError, ToolSpec
from app.core.serialization import bounded, jsonable, summarize


def _error_envelope(error: ToolError) -> str:
    return json.dumps(
        {"ok": False, "error": {"code": error.code, "message": error.message, "retryable": error.retryable}}
    )


def _classify(exc: BaseException, tool_name: str, timeout: float) -> ToolError:
    if isinstance(exc, ToolError):
        return exc
    if isinstance(exc, TimeoutError):
        return ToolError("timeout", f"{tool_name} did not finish within {timeout:g}s", retryable=True)
    if isinstance(exc, ModelBehaviorError):
        return ToolError("invalid_arguments", str(exc))
    return ToolError("internal_error", f"{type(exc).__name__}: {exc}")


def _parse_arguments(input_json: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(input_json) if input_json.strip() else {}
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def instrument_tool(spec: ToolSpec, settings: Settings) -> FunctionTool:
    base = function_tool(
        spec.fn,
        name_override=spec.name,
        description_override=spec.description,
        failure_error_function=None,
        strict_mode=True,
    )
    original: Callable[[ToolContext[Any], str], Awaitable[Any]] = base.on_invoke_tool
    timeout = settings.tool_timeout_seconds
    max_attempts = settings.tool_max_retries + 1

    async def instrumented(ctx: ToolContext[RunContext], input_json: str) -> str:
        run_ctx = ctx.context
        base_payload = {"call_id": ctx.tool_call_id, "tool": spec.name, "label": spec.label}
        arguments = _parse_arguments(input_json)
        run_ctx.stats.tool_calls += 1
        await run_ctx.emit(
            "tool_started", {**base_payload, "arguments": bounded(arguments, settings.tool_result_max_chars)[0]}
        )
        if arguments is None:
            error = ToolError("invalid_arguments", "Tool arguments must be a JSON object")
            run_ctx.stats.tool_failures += 1
            await run_ctx.emit(
                "tool_failed",
                {
                    **base_payload,
                    "attempt": 1,
                    "duration_ms": 0,
                    "will_retry": False,
                    "error": {"code": error.code, "message": error.message},
                },
            )
            return _error_envelope(error)

        for attempt in range(1, max_attempts + 1):
            started = time.perf_counter()
            try:
                result = await asyncio.wait_for(original(ctx, input_json), timeout)
            except Exception as exc:
                error = _classify(exc, spec.name, timeout)
                duration_ms = int((time.perf_counter() - started) * 1000)
                will_retry = error.retryable and attempt < max_attempts
                run_ctx.stats.tool_failures += 1
                await run_ctx.emit(
                    "tool_failed",
                    {
                        **base_payload,
                        "attempt": attempt,
                        "duration_ms": duration_ms,
                        "will_retry": will_retry,
                        "error": {"code": error.code, "message": error.message},
                    },
                )
                if not will_retry:
                    return _error_envelope(error)
                continue
            duration_ms = int((time.perf_counter() - started) * 1000)
            data, truncated = bounded(result, settings.tool_result_max_chars)
            await run_ctx.emit(
                "tool_finished",
                {
                    **base_payload,
                    "attempt": attempt,
                    "duration_ms": duration_ms,
                    "summary": summarize(jsonable(result)),
                    "result": data,
                    "truncated": truncated,
                },
            )
            return json.dumps({"ok": True, "data": data, "truncated": truncated}, ensure_ascii=False)
        raise AssertionError("unreachable")

    base.on_invoke_tool = instrumented
    return base


def instrument_tools(specs: list[ToolSpec], settings: Settings) -> list[FunctionTool]:
    return [instrument_tool(spec, settings) for spec in specs]
