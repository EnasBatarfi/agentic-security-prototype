from django.conf import settings
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic


def get_chat_model():
    """Create the configured chat model."""

    # If the provider is OpenAI, return the OpenAI chat model with the appropriate settings
    if settings.LLM_PROVIDER == "openai":
        print(f"Using LLM provider: openai | model: {settings.OPENAI_MODEL}")
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )

    # If the provider is Anthropic, return the Anthropic chat model with the appropriate settings
    if settings.LLM_PROVIDER == "anthropic":
        print(f"Using LLM provider: anthropic | model: {settings.ANTHROPIC_MODEL}")
        return ChatAnthropic(
            model=settings.ANTHROPIC_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=0,
        )

    # Otherwise, return the local Ollama chat model
    print(f"Using local LLM provider: ollama | model: {settings.OLLAMA_MODEL}")
    return ChatOllama(
        model=settings.OLLAMA_MODEL,
        # Temperature is set to 0 to make the model's responses more deterministic and less random
        temperature=0,
    )