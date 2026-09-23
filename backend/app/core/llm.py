import json
from collections.abc import Callable
from dataclasses import replace
from urllib.parse import urlsplit

from agents import Model, set_default_openai_api, set_default_openai_client, set_tracing_disabled
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from app.config import Settings
from app.core.contracts import DomainModule
from app.core.errors import InvalidOutputError
from app.core.read_models import RunDTO
from app.speech.guard import is_loopback

SCRIPTED_PREFIX = "scripted:"


def configure_model_provider(settings: Settings) -> None:
    set_tracing_disabled(True)
    endpoint = settings.openai_base_url or "http://localhost:11434/v1"
    url = urlsplit(endpoint)
    if url.scheme != "http" or not is_loopback((url.hostname, url.port or 80)) or url.port != 11434:
        raise ValueError("LLM endpoint must be local Ollama on http://localhost:11434/v1")
    if url.path.rstrip("/") != "/v1" or url.username or url.password or url.query or url.fragment:
        raise ValueError("LLM endpoint must use the Ollama /v1 API")
    client = AsyncOpenAI(base_url=endpoint, api_key=settings.openai_api_key or "ollama")
    set_default_openai_client(client, use_for_tracing=False)
    set_default_openai_api("chat_completions")



class OllamaProtocolModel(OpenAIChatCompletionsModel):
    """Use tool grammar for investigation and JSON grammar for the final protocol."""

    async def get_response(self, *args, **kwargs):
        items = kwargs.get("input", [])
        calls = {item.get("call_id"): item.get("name") for item in items if isinstance(item, dict) and item.get("type") == "function_call"} if isinstance(items, list) else {}
        completed = set()
        not_ready = False
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict) or item.get("type") != "function_call_output":
                continue
            try:
                result = json.loads(item.get("output", "{}"))
            except (TypeError, ValueError):
                continue
            if not isinstance(result, dict):
                continue
            if result.get("ok"):
                tool_name = calls.get(item.get("call_id"))
                if tool_name == "read_transcript":
                    data = result.get("data")
                    if not isinstance(data, dict) or result.get("truncated") or data.get("next_offset") is not None:
                        continue
                completed.add(tool_name)
            elif isinstance(result.get("error"), dict) and result["error"].get("code") == "not_ready":
                not_ready = True
        settings = kwargs["model_settings"]
        final_phase = not_ready or {"get_meeting", "read_transcript"} <= completed
        if final_phase:
            kwargs["model_settings"] = replace(settings, extra_body=None, tool_choice="none")
        else:
            tool = "get_meeting" if "get_meeting" not in completed else "read_transcript"
            kwargs["model_settings"] = replace(settings, extra_body={"response_format": None}, tool_choice=tool)
        response = await super().get_response(*args, **kwargs)
        if final_phase:
            text = "".join(
                part.text
                for item in response.output if item.type == "message"
                for part in item.content if part.type == "output_text"
            )
            try:
                json.loads(text)
            except (TypeError, ValueError) as exc:
                raise InvalidOutputError(
                    "Модель вернула незавершённый или некорректный JSON. Выполните make llm, "
                    "установите OPENAI_MODEL=protokol-qwen3.5:4b и перезапустите API. "
                    "Если ошибка повторится, сократите стенограмму и повторите."
                ) from exc
        return response


def default_model_factory(settings: Settings, domain: DomainModule) -> Callable[[RunDTO], str | Model]:
    name = settings.openai_model
    if name.startswith(SCRIPTED_PREFIX):
        key = name[len(SCRIPTED_PREFIX) :]
        if key == "auto" and domain.auto_script is not None:
            return lambda run: domain.auto_script(run.case_ref, run.input)
        if key not in domain.scripts:
            raise ValueError(f"Unknown scripted model '{key}'. Available: auto, {', '.join(sorted(domain.scripts))}")
        return lambda run: domain.scripts[key]()
    client = AsyncOpenAI(base_url=settings.openai_base_url or "http://localhost:11434/v1", api_key=settings.openai_api_key or "ollama")
    return lambda run: OllamaProtocolModel(model=name, openai_client=client) if domain.key == "protokol" else name
