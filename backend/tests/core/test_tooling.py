import asyncio
import json
import uuid

import pytest
from agents import RunContextWrapper
from agents.tool_context import ToolContext

from app.config import Settings
from app.core.context import RunContext
from app.core.contracts import ToolError, ToolSpec, TransientToolError
from app.core.tooling import instrument_tool


class Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def __call__(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))

    def types(self) -> list[str]:
        return [t for t, _ in self.events]


def make_ctx(recorder: Recorder) -> tuple[RunContext, ToolContext]:
    run_ctx = RunContext(run_id=uuid.uuid4(), case_ref="case-1", case_input=None, session_factory=None, emit=recorder)
    tool_ctx = ToolContext(
        context=run_ctx, tool_name="probe", tool_call_id="call-1", tool_arguments='{"case_id": "c1"}'
    )
    return run_ctx, tool_ctx


def settings(**overrides) -> Settings:
    return Settings(**{"tool_timeout_seconds": 0.2, "tool_max_retries": 1, "tool_result_max_chars": 300, **overrides})


async def invoke(tool, tool_ctx, args: dict | None = None) -> dict:
    raw = await tool.on_invoke_tool(tool_ctx, json.dumps(args or {"case_id": "c1"}))
    return json.loads(raw)


async def test_should_wrap_success_in_an_ok_envelope_and_emit_started_and_finished() -> None:
    async def probe(ctx: RunContextWrapper[RunContext], case_id: str) -> dict:
        """Probe a case."""
        return {"case": case_id}

    recorder = Recorder()
    run_ctx, tool_ctx = make_ctx(recorder)
    tool = instrument_tool(ToolSpec(name="probe", label="Probing the case", fn=probe), settings())
    result = await invoke(tool, tool_ctx)

    assert result == {"ok": True, "data": {"case": "c1"}, "truncated": False}
    assert recorder.types() == ["tool_started", "tool_finished"]
    started, finished = recorder.events[0][1], recorder.events[1][1]
    assert started == {
        "call_id": "call-1",
        "tool": "probe",
        "label": "Probing the case",
        "arguments": {"case_id": "c1"},
    }
    assert finished["attempt"] == 1 and finished["duration_ms"] >= 0 and finished["result"] == {"case": "c1"}
    assert run_ctx.stats.tool_calls == 1


async def test_should_keep_the_parameter_schema_of_the_original_function() -> None:
    async def probe(ctx: RunContextWrapper[RunContext], case_id: str) -> dict:
        """Probe a case."""
        return {}

    tool = instrument_tool(ToolSpec(name="probe", label="Probing", fn=probe), settings())
    assert "case_id" in tool.params_json_schema["properties"]
    assert tool.name == "probe" and tool.description == "Probe a case."


async def test_should_return_a_structured_error_without_retry_for_tool_errors() -> None:
    async def probe(ctx: RunContextWrapper[RunContext], case_id: str) -> dict:
        raise ToolError("not_found", f"No case {case_id}")

    recorder = Recorder()
    run_ctx, tool_ctx = make_ctx(recorder)
    result = await invoke(instrument_tool(ToolSpec(name="probe", label="Probing", fn=probe), settings()), tool_ctx)

    assert result == {"ok": False, "error": {"code": "not_found", "message": "No case c1", "retryable": False}}
    assert recorder.types() == ["tool_started", "tool_failed"]
    assert recorder.events[1][1]["will_retry"] is False
    assert run_ctx.stats.tool_failures == 1


async def test_should_retry_transient_errors_and_succeed_on_the_next_attempt() -> None:
    attempts = {"n": 0}

    async def probe(ctx: RunContextWrapper[RunContext], case_id: str) -> dict:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise TransientToolError("db_busy", "try again")
        return {"attempt": attempts["n"]}

    recorder = Recorder()
    _, tool_ctx = make_ctx(recorder)
    result = await invoke(instrument_tool(ToolSpec(name="probe", label="Probing", fn=probe), settings()), tool_ctx)

    assert result["ok"] is True and result["data"] == {"attempt": 2}
    assert recorder.types() == ["tool_started", "tool_failed", "tool_finished"]
    assert recorder.events[1][1]["will_retry"] is True and recorder.events[1][1]["attempt"] == 1
    assert recorder.events[2][1]["attempt"] == 2


async def test_should_give_up_after_the_configured_retries() -> None:
    async def probe(ctx: RunContextWrapper[RunContext], case_id: str) -> dict:
        raise TransientToolError("db_busy", "still busy")

    recorder = Recorder()
    _, tool_ctx = make_ctx(recorder)
    result = await invoke(instrument_tool(ToolSpec(name="probe", label="Probing", fn=probe), settings()), tool_ctx)

    assert result["ok"] is False and result["error"]["retryable"] is True
    assert recorder.types() == ["tool_started", "tool_failed", "tool_failed"]
    assert [e["will_retry"] for _, e in recorder.events[1:]] == [True, False]


async def test_should_time_out_slow_tools_and_report_a_timeout_code() -> None:
    async def probe(ctx: RunContextWrapper[RunContext], case_id: str) -> dict:
        await asyncio.sleep(5)
        return {}

    recorder = Recorder()
    _, tool_ctx = make_ctx(recorder)
    result = await invoke(
        instrument_tool(ToolSpec(name="probe", label="Probing", fn=probe), settings(tool_max_retries=0)), tool_ctx
    )

    assert result["ok"] is False and result["error"]["code"] == "timeout"
    assert recorder.types() == ["tool_started", "tool_failed"]


async def test_should_truncate_oversized_results_and_flag_it() -> None:
    async def probe(ctx: RunContextWrapper[RunContext], case_id: str) -> dict:
        return {"rows": ["x" * 50] * 20}

    recorder = Recorder()
    _, tool_ctx = make_ctx(recorder)
    result = await invoke(instrument_tool(ToolSpec(name="probe", label="Probing", fn=probe), settings()), tool_ctx)

    assert result["ok"] is True and result["truncated"] is True
    assert len(json.dumps(result["data"])) <= 300 + 50
    assert recorder.events[1][1]["truncated"] is True


async def test_should_convert_unexpected_exceptions_into_internal_errors() -> None:
    async def probe(ctx: RunContextWrapper[RunContext], case_id: str) -> dict:
        raise RuntimeError("boom")

    recorder = Recorder()
    _, tool_ctx = make_ctx(recorder)
    result = await invoke(instrument_tool(ToolSpec(name="probe", label="Probing", fn=probe), settings()), tool_ctx)

    assert result["ok"] is False and result["error"]["code"] == "internal_error"
    assert "boom" in result["error"]["message"]
    assert recorder.types() == ["tool_started", "tool_failed"]


async def test_should_return_an_invalid_arguments_error_when_the_model_sends_bad_json() -> None:
    async def probe(ctx: RunContextWrapper[RunContext], case_id: str) -> dict:
        return {}

    recorder = Recorder()
    _, tool_ctx = make_ctx(recorder)
    raw = await instrument_tool(ToolSpec(name="probe", label="Probing", fn=probe), settings()).on_invoke_tool(
        tool_ctx, '{"case_id": 5'
    )
    result = json.loads(raw)
    assert result["ok"] is False and result["error"]["code"] == "invalid_arguments"


@pytest.mark.parametrize("value", [None, 3, "text", [1, 2]])
async def test_should_serialize_non_dict_results_as_data(value) -> None:
    async def probe(ctx: RunContextWrapper[RunContext], case_id: str):
        return value

    recorder = Recorder()
    _, tool_ctx = make_ctx(recorder)
    result = await invoke(instrument_tool(ToolSpec(name="probe", label="Probing", fn=probe), settings()), tool_ctx)
    assert result["data"] == value
