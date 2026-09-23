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


@pytest.mark.parametrize("endpoint", ["https://api.openai.com/v1", "http://192.168.1.1:11434/v1", "http://localhost:80/v1"])
def test_external_llm_endpoint_rejected(endpoint):
    with pytest.raises(ValueError, match="local Ollama"):
        configure_model_provider(Settings(openai_base_url=endpoint))
