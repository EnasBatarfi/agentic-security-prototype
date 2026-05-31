from django.conf import settings
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI


def get_chat_model():
    """Create the configured chat model."""

    # if the provider is ollama, use the ChatOllama class and configure it with the model name from settings 
    if settings.LLM_PROVIDER == "ollama":
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            # temperature is set to 0 to make the model's responses more deterministic and less random 
            temperature=0,
        )

    # otherwise, default to using the OpenAI provider and configure the ChatOpenAI class with model name and the API key from settings
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )