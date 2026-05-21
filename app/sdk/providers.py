from enum import StrEnum


class Provider(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"


# LiteLLM model strings are "{provider}/{model_id}" where model_id is the
# provider's own identifier. Keep this list in sync with what each provider
# actually exposes — the frontend reads it via GET /api/v1/providers.
SUPPORTED_MODELS: dict[str, list[str]] = {
    Provider.ANTHROPIC: [
        "claude-haiku-4-5",
    ],
    Provider.OPENAI: [
        "gpt-4.1-mini",
    ],
    Provider.GEMINI: [
        "gemini-2.5-flash",
    ],
}


def litellm_model_string(provider: str, model: str) -> str:
    """Return the model string LiteLLM expects, e.g. 'anthropic/claude-sonnet-4-5'."""
    return f"{provider}/{model}"


def validate_provider_model(provider: str, model: str) -> None:
    """Raise ValueError if the provider/model combination is not in SUPPORTED_MODELS."""
    if provider not in SUPPORTED_MODELS:
        supported = [str(k) for k in SUPPORTED_MODELS]
        raise ValueError(f"Unsupported provider '{provider}'. Supported: {supported}")
    if model not in SUPPORTED_MODELS[provider]:
        supported = SUPPORTED_MODELS[provider]
        raise ValueError(f"Unsupported model '{model}' for provider '{provider}'. Supported: {supported}")
