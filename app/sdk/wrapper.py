import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime

import litellm
import litellm.exceptions

from app.sdk.providers import litellm_model_string, validate_provider_model

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
class StreamResult:
    """Populated in-place as ChatStream is iterated. Read .result after exhaustion."""
    request_at: datetime
    content: str = field(default="")
    prompt_tokens: int | None = field(default=None)
    completion_tokens: int | None = field(default=None)
    total_tokens: int | None = field(default=None)
    latency_ms: int | None = field(default=None)
    response_at: datetime | None = field(default=None)


class ChatStream:
    """
    Wraps a LiteLLM async stream. Yields raw content chunks (str) and
    populates .result with timing + token usage after the iterator is exhausted.
    """

    def __init__(self, litellm_stream, request_at: datetime, start: float) -> None:
        self._stream = litellm_stream
        self._start = start
        self.result = StreamResult(request_at=request_at)

    def __aiter__(self) -> AsyncIterator[str]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[str]:
        async for chunk in self._stream:
            delta = chunk.choices[0].delta.content or ""

            if getattr(chunk, "usage", None) is not None:
                self.result.prompt_tokens = chunk.usage.prompt_tokens
                self.result.completion_tokens = chunk.usage.completion_tokens
                self.result.total_tokens = chunk.usage.total_tokens

            if delta:
                self.result.content += delta
                yield delta

        self.result.latency_ms = int((time.monotonic() - self._start) * 1000)
        self.result.response_at = datetime.now(UTC)


class LLMWrapper:
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
            raise LLMAuthError(str(e), int((time.monotonic() - start) * 1000), request_at)
        except litellm.exceptions.RateLimitError as e:
            raise LLMRateLimitError(str(e), int((time.monotonic() - start) * 1000), request_at)
        except litellm.exceptions.ContextWindowExceededError as e:
            raise LLMContextError(str(e), int((time.monotonic() - start) * 1000), request_at)
        except Exception as e:
            raise LLMProviderError(str(e), int((time.monotonic() - start) * 1000), request_at)

        latency_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage

        return LLMCallResult(
            content=response.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            latency_ms=latency_ms,
            request_at=request_at,
            response_at=datetime.now(UTC),
        )

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        provider: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ChatStream:
        validate_provider_model(provider, model)
        model_string = litellm_model_string(provider, model)

        request_at = datetime.now(UTC)
        start = time.monotonic()

        try:
            stream = await litellm.acompletion(
                model=model_string,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
        except litellm.exceptions.AuthenticationError as e:
            raise LLMAuthError(str(e), int((time.monotonic() - start) * 1000), request_at)
        except litellm.exceptions.RateLimitError as e:
            raise LLMRateLimitError(str(e), int((time.monotonic() - start) * 1000), request_at)
        except litellm.exceptions.ContextWindowExceededError as e:
            raise LLMContextError(str(e), int((time.monotonic() - start) * 1000), request_at)
        except Exception as e:
            raise LLMProviderError(str(e), int((time.monotonic() - start) * 1000), request_at)

        return ChatStream(stream, request_at, start)


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


llm_wrapper = LLMWrapper()
