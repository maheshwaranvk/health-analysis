"""
Security and governance utilities.

Provides PII redaction, prompt-injection detection, and output safety
scanning for the health-data governance layer.
"""

import re

from app.core.logging_config import logger

# ── Forbidden phrases in LLM output that indicate unsafe medical content ─
UNSAFE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(diagnos(e|is|ed|ing))\b", re.IGNORECASE),
    re.compile(r"\b(prescri(be|bed|ption))\b", re.IGNORECASE),
    re.compile(r"\byou\s+(have|suffer\s+from|are\s+diagnosed)\b", re.IGNORECASE),
    re.compile(r"\b(take|start|stop)\s+\w*\s*(medication|drug|medicine|pill)\b", re.IGNORECASE),
    re.compile(r"\b(I am a doctor|as a physician|medical professional)\b", re.IGNORECASE),
]

# ── Prompt-injection patterns ────────────────────────────────────────
INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous\s+)?instructions", re.IGNORECASE),
    re.compile(r"show\s+all\s+records", re.IGNORECASE),
    re.compile(r"reveal\s+(system|internal)\s+prompt", re.IGNORECASE),
    re.compile(r"forget\s+(your|all)\s+(rules|instructions)", re.IGNORECASE),
]

DISCLAIMER = (
    "This analysis is generated from the provided dataset for informational "
    "purposes only and is not medical advice. Please consult a qualified "
    "healthcare professional for clinical decisions."
)


def redact_patient_ids(text: str) -> str:
    """Replace literal patient numbers with [REDACTED] before sending to LLM."""
    return re.sub(r"\bPatient[_\s]?(?:Number|Id|ID)?[:\s]*\d+", "[REDACTED]", text)


def detect_prompt_injection(text: str) -> bool:
    """Return True if the text looks like a prompt-injection attempt."""
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning("Prompt injection detected: %s", pattern.pattern)
            return True
    return False


def scan_output_safety(text: str) -> list[str]:
    """
    Scan LLM-generated text for unsafe medical claims.

    Returns a list of safety-flag descriptions. Empty list = safe.
    """
    flags: list[str] = []
    for pattern in UNSAFE_PATTERNS:
        if pattern.search(text):
            flags.append(f"Matched unsafe pattern: {pattern.pattern}")
    return flags


def make_safe_response(
    insights: str,
    recommendations: list[str],
    safety_flags: list[str],
) -> tuple[str, list[str], list[str]]:
    """
    If safety flags are present, replace the unsafe LLM output with
    a generic safe version. Never return unsafe text to the user.

    Returns:
        (safe_insights, safe_recommendations, final_safety_flags)
    """
    if not safety_flags:
        return insights, recommendations, safety_flags

    logger.warning("Unsafe LLM output detected and hard-blocked: %s", safety_flags)

    safe_insights = (
        "The analysis results are available above. "
        "For a detailed interpretation, please consult a qualified healthcare professional."
    )
    safe_recommendations = [
        "Consider discussing these findings with a healthcare provider.",
        "Maintain a balanced diet and regular physical activity.",
    ]
    return safe_insights, safe_recommendations, safety_flags
