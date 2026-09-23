import pytest

from app.config import Settings
from app.core.llm import configure_model_provider


@pytest.mark.parametrize("endpoint", ["http://localhost:11434/v1", None])
def test_local_base_url_switches_to_chat_completions(monkeypatch, endpoint):
    calls = []
    monkeypatch.setattr(
        "app.core.llm.set_default_openai_client",
        lambda client, use_for_tracing: calls.append(("client", str(client.base_url), use_for_tracing)),
    )
    monkeypatch.setattr("app.core.llm.set_default_openai_api", lambda api: calls.append(("api", api)))
    monkeypatch.setattr("app.core.llm.set_tracing_disabled", lambda disabled: calls.append(("tracing", disabled)))
    settings = Settings(openai_api_key="ollama", openai_base_url=endpoint, openai_model="qwen3.5:4b")
    configure_model_provider(settings)
    assert ("api", "chat_completions") in calls
    assert ("tracing", True) in calls
    assert ("client", "http://localhost:11434/v1/", False) in calls


@pytest.mark.parametrize(
    "endpoint", ["https://api.openai.com/v1", "http://192.168.1.1:11434/v1", "http://localhost:80/v1"]
)
def test_external_llm_endpoint_rejected(endpoint):
    with pytest.raises(ValueError, match="local Ollama"):
        configure_model_provider(Settings(openai_base_url=endpoint))


def _tool_result(name, *, ok=True, error=None):
    import json

    call_id = "call-" + name
    return [
        {"type": "function_call", "call_id": call_id, "name": name, "arguments": "{}"},
        {
            "type": "function_call_output",
            "call_id": call_id,
            "output": json.dumps(
                {"ok": ok, "data": {"segments": [], "next_offset": None}, "error": error, "truncated": False}
            ),
        },
    ]


@pytest.mark.parametrize(
    "items, tool, final",
    [
        ([], "get_meeting", False),
        (_tool_result("get_meeting"), "read_transcript", False),
        (_tool_result("read_transcript"), "get_meeting", False),
        (_tool_result("get_meeting") + _tool_result("read_transcript"), "none", True),
        (_tool_result("get_meeting", ok=False, error={"code": "not_ready"}), "none", True),
        (_tool_result("get_meeting", ok=False, error={"code": "timeout"}), "get_meeting", False),
    ],
)
async def test_ollama_model_separates_tool_and_final_json_grammar(monkeypatch, items, tool, final):
    from agents import ModelSettings
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai.types.shared import Reasoning

    from app.core.llm import OllamaProtocolModel

    captured = {}
    from types import SimpleNamespace

    sentinel = SimpleNamespace(output=[SimpleNamespace(type="message", content=[SimpleNamespace(type="output_text", text='{"outcome":"needs_input"}')])])

    async def capture(self, *args, **kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(OpenAIChatCompletionsModel, "get_response", capture)
    model = OllamaProtocolModel(model="qwen3.5:4b", openai_client=object())
    settings = ModelSettings(reasoning=Reasoning(effort="none"), max_tokens=5000)
    output_schema = object()
    response = await model.get_response(input=items, model_settings=settings, output_schema=output_schema)
    assert response is sentinel
    assert captured["model_settings"].tool_choice == tool
    assert captured["model_settings"].extra_body == (None if final else {"response_format": None})
    assert captured["model_settings"].reasoning.effort == "none"
    assert captured["model_settings"].max_tokens == 5000
    assert captured["output_schema"] is output_schema
    assert settings.tool_choice is None and settings.extra_body is None


def test_ollama_factory_builds_local_model_without_network():
    from app.core.llm import OllamaProtocolModel, default_model_factory
    from app.domain import DOMAIN

    model = default_model_factory(
        Settings(openai_model="qwen3.5:4b", openai_base_url="http://localhost:11434/v1"), DOMAIN
    )(None)
    assert isinstance(model, OllamaProtocolModel)
    assert str(model._client.base_url) == "http://localhost:11434/v1/"


@pytest.mark.parametrize("text, valid", [('{"outcome":"proposal_ready"}', True), ('{"outcome":', False), ('', False)])
async def test_final_json_is_checked_before_agent_parsing(monkeypatch, text, valid):
    from agents import ModelSettings
    from agents.items import ModelResponse
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from agents.usage import Usage
    from openai.types.responses import ResponseOutputMessage, ResponseOutputText

    from app.core.errors import InvalidOutputError
    from app.core.llm import OllamaProtocolModel

    response = ModelResponse(output=[ResponseOutputMessage(
        id="msg", type="message", role="assistant", status="completed",
        content=[ResponseOutputText(type="output_text", text=text, annotations=[])],
    )], usage=Usage(), response_id=None)

    async def respond(self, *args, **kwargs):
        return response

    monkeypatch.setattr(OpenAIChatCompletionsModel, "get_response", respond)
    model = OllamaProtocolModel(model="local", openai_client=object())
    request = dict(input=_tool_result("get_meeting") + _tool_result("read_transcript"), model_settings=ModelSettings())
    if valid:
        assert await model.get_response(**request) is response
    else:
        with pytest.raises(InvalidOutputError, match="make llm") as error:
            await model.get_response(**request)
        assert "OPENAI_MODEL=protokol-qwen3.5:4b" in str(error.value)


@pytest.mark.parametrize("data", [None, [], "truncated text"])
async def test_malformed_transcript_data_keeps_read_phase(monkeypatch, data):
    import json

    from agents import ModelSettings
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

    from app.core.llm import OllamaProtocolModel

    captured = {}

    async def respond(self, *args, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(OpenAIChatCompletionsModel, "get_response", respond)
    items = _tool_result("get_meeting") + _tool_result("read_transcript")
    items[-1]["output"] = json.dumps({"ok": True, "data": data})
    await OllamaProtocolModel(model="local", openai_client=object()).get_response(input=items, model_settings=ModelSettings())
    assert captured["model_settings"].tool_choice == "read_transcript"
