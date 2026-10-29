"""Thin provider wrapper. Swapping to OpenAI means writing another class with the same complete() signature."""
import anthropic

from ..core.config import settings


class LLMError(Exception):
    """Raised for ANY failure (missing key, timeout, rate limit, API down) so callers degrade gracefully."""


class AnthropicClient:
    def __init__(self) -> None:
        if not settings.anthropic_api_key:
            raise LLMError("ANTHROPIC_API_KEY is not configured")
        # max_retries gives exponential backoff on 429/5xx/connection errors.
        self._client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.ai_timeout_seconds,
            max_retries=2,
        )

    def complete(self, system: str, user: str, max_tokens: int) -> str:
        try:
            resp = self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=max_tokens,
                # cache_control lets the provider reuse the static system prompt across calls.
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError as exc:
            raise LLMError(f"{type(exc).__name__}: {exc}") from exc
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        if not text:
            raise LLMError("Empty response from model")
        return text


def get_client() -> AnthropicClient:
    return AnthropicClient()
