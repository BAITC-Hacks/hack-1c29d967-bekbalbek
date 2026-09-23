from collections.abc import Callable
from urllib.parse import urlsplit

from agents import Model, set_default_openai_api, set_default_openai_client, set_tracing_disabled
from openai import AsyncOpenAI

from app.config import Settings
from app.core.contracts import DomainModule
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


def default_model_factory(settings: Settings, domain: DomainModule) -> Callable[[RunDTO], str | Model]:
    name = settings.openai_model
    if name.startswith(SCRIPTED_PREFIX):
        key = name[len(SCRIPTED_PREFIX) :]
        if key == "auto" and domain.auto_script is not None:
            return lambda run: domain.auto_script(run.case_ref, run.input)
        if key not in domain.scripts:
            raise ValueError(f"Unknown scripted model '{key}'. Available: auto, {', '.join(sorted(domain.scripts))}")
        return lambda run: domain.scripts[key]()
    return lambda run: name
