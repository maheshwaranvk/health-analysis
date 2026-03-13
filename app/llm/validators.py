"""
Output validators.

Validates LLM-generated responses for safety before returning to users.
Hard-blocks unsafe content and replaces it with a safe version.
"""

from typing import Any

from app.core.security import scan_output_safety, make_safe_response, DISCLAIMER
from app.core.metrics import metrics
from app.core.logging_config import logger


def validate_and_safe_guard(
    insights: str,
    recommendations: list[str],
) -> tuple[str, list[str], list[str]]:
    """
    Run safety scanning on LLM output.  If unsafe patterns are found,
    hard-block the original text and return a safe replacement.

    Returns:
        (final_insights, final_recommendations, safety_flags)
    """
    # Scan insights
    flags = scan_output_safety(insights)

    # Scan each recommendation
    for rec in recommendations:
        flags.extend(scan_output_safety(rec))

    if flags:
        metrics.record_safety_violation()
        logger.warning("Safety violations detected (%d flags), hard-blocking output", len(flags))

    safe_insights, safe_recs, final_flags = make_safe_response(
        insights, recommendations, flags
    )
    return safe_insights, safe_recs, final_flags
