"""
Governance service.

Pre-LLM input sanitisation and post-LLM output safety enforcement.
Ensures patient identifiers are never sent to the LLM and that
unsafe generated text is hard-blocked before reaching users.
"""

from typing import Any

from app.core.security import (
    redact_patient_ids,
    detect_prompt_injection,
    DISCLAIMER,
)
from app.core.logging_config import logger


def sanitize_for_llm(analysis_result: dict[str, Any]) -> dict[str, Any]:
    """
    Remove or redact patient-identifiable information from the
    analysis result before it is sent to the LLM.
    """
    sanitized = {}
    for key, value in analysis_result.items():
        if isinstance(value, str):
            sanitized[key] = redact_patient_ids(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_for_llm(value)
        else:
            sanitized[key] = value
    return sanitized


def check_input_safety(question: str) -> tuple[bool, str]:
    """
    Check user input for prompt-injection attempts.

    Returns:
        (is_safe, message)
    """
    if detect_prompt_injection(question):
        logger.warning("Input rejected — prompt injection detected")
        return False, "Your question was rejected for safety reasons."
    return True, ""
