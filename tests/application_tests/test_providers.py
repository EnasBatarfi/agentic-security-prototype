"""Check that each model provider receives the right settings."""

import pytest

from apps.agents import providers


@pytest.mark.parametrize(
    ("provider", "constructor_name", "model_setting", "key_setting"),
    [
        ("openai", "ChatOpenAI", "OPENAI_MODEL", "OPENAI_API_KEY"),
        ("anthropic", "ChatAnthropic", "ANTHROPIC_MODEL", "ANTHROPIC_API_KEY"),
    ],
)
def test_remote_provider_configuration(monkeypatch, settings, provider, constructor_name, model_setting, key_setting):
    """Check that the remote provider uses the configured settings."""
    settings.LLM_PROVIDER = provider
    setattr(settings, model_setting, "test-model")
    setattr(settings, key_setting, "test-key")
    captured = {}
    expected = object()

    def constructor(**kwargs):
        """Capture the settings given to the provider."""

        captured.update(kwargs)
        return expected

    monkeypatch.setattr(providers, constructor_name, constructor)

    assert providers.get_chat_model() is expected
    assert captured == {
        "model": "test-model",
        "api_key": "test-key",
        "temperature": 0,
    }


def test_ollama_provider_configuration(monkeypatch, settings):
    """Check that Ollama provider configuration."""
    settings.LLM_PROVIDER = "ollama"
    settings.OLLAMA_MODEL = "local-test-model"
    captured = {}
    expected = object()
    monkeypatch.setattr(
        providers,
        "ChatOllama",
        lambda **kwargs: captured.update(kwargs) or expected,
    )

    assert providers.get_chat_model() is expected
    assert captured == {"model": "local-test-model", "temperature": 0}
