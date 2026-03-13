"""
OpenAI client wrapper.

Provides a single reusable interface for LLM calls with timeout,
retry, and latency tracking.  Returns None gracefully when no API
key is configured (no-key mode).
"""

import time
from typing import Optional

from app.core.config import settings
from app.core.logging_config import logger
from app.core.metrics import metrics


def _get_client():
    """Lazily import and return an OpenAI client, or None."""
    if not settings.has_openai_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(
            api_key=settings.openai_api_key,
            timeout=30.0,
        )
    except Exception as exc:
        logger.error("Failed to create OpenAI client: %s", exc)
        return None


def call_llm(
    system_prompt: str,
    user_message: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Optional[str]:
    """
    Send a chat-completion request to OpenAI.

    Returns the assistant message content, or None if the LLM is
    unavailable or the call fails.
    """
    client = _get_client()
    if client is None:
        logger.info("LLM call skipped — no OpenAI key configured (no-key mode)")
        return None

    temp = temperature if temperature is not None else settings.llm_temperature
    tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

    start = time.time()
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temp,
            max_tokens=tokens,
        )
        content = response.choices[0].message.content
        elapsed = time.time() - start

        metrics.record_llm_call()
        metrics.record_latency(elapsed)

        logger.info("LLM call completed in %.2fs", elapsed)
        return content

    except Exception as exc:
        elapsed = time.time() - start
        logger.error("LLM call failed after %.2fs: %s", elapsed, exc)
        return None
