import time
from dataclasses import dataclass
from datetime import UTC, datetime

import litellm
import litellm.exceptions

from app.sdk.providers import litellm_model_string, validate_provider_model

# Suppress LiteLLM's own stdout logging — we do our own.
litellm.suppress_debug_info = True


@dataclass
class LLMCallResult:
    content: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_ms: int
    request_at: datetime
    response_at: datetime


@dataclass
class LLMCallError:
    error_message: str
    latency_ms: int
    request_at: datetime
    response_at: datetime


class LLMWrapper:
    """
    Thin wrapper around LiteLLM. Owns timing, usage extraction, and error
    normalisation. Phase 3 adds stream_chat(); this method stays non-streaming.
    """

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        provider: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMCallResult:
        validate_provider_model(provider, model)
        model_string = litellm_model_string(provider, model)

        request_at = datetime.now(UTC)
        start = time.monotonic()

        try:
            response = await litellm.acompletion(
                model=model_string,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except litellm.exceptions.AuthenticationError as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            raise LLMAuthError(str(e), latency_ms, request_at)
        except litellm.exceptions.RateLimitError as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            raise LLMRateLimitError(str(e), latency_ms, request_at)
        except litellm.exceptions.ContextWindowExceededError as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            raise LLMContextError(str(e), latency_ms, request_at)
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            raise LLMProviderError(str(e), latency_ms, request_at)

        latency_ms = int((time.monotonic() - start) * 1000)
        response_at = datetime.now(UTC)

        content = response.choices[0].message.content or ""
        usage = response.usage

        return LLMCallResult(
            content=content,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            latency_ms=latency_ms,
            request_at=request_at,
            response_at=response_at,
        )


# --- Typed exceptions so route handlers can return precise HTTP status codes ---

class LLMError(Exception):
    def __init__(self, message: str, latency_ms: int, request_at: datetime):
        super().__init__(message)
        self.latency_ms = latency_ms
        self.request_at = request_at


class LLMAuthError(LLMError):
    """401 — bad or missing API key."""


class LLMRateLimitError(LLMError):
    """429 — provider rate limit hit."""


class LLMContextError(LLMError):
    """422 — messages exceed the model's context window."""


class LLMProviderError(LLMError):
    """502 — generic upstream provider failure."""


# Module-level singleton — imported by route handlers.
llm_wrapper = LLMWrapper()
