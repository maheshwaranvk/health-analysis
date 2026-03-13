"""
Responder module.

Takes structured analysis results and generates a natural-language
response using the LLM (when available) or deterministic rule-based
templates (no-key mode).
"""

import json
import re
from typing import Any, Optional

from app.llm.client import call_llm
from app.llm.prompts import responder_system_prompt, safety_rules_text
from app.core.config import settings
from app.core.logging_config import logger
from app.core.security import DISCLAIMER


# ── Deterministic rule-based response (no-key mode) ─────────────────
def _rule_based_response(
    intent: str,
    analysis_result: dict[str, Any],
) -> dict[str, Any]:
    """Generate insights and recommendations without the LLM."""
    recs: list[str] = [
        "Consider maintaining regular physical activity.",
        "A balanced diet low in sodium may support cardiovascular health.",
    ]
    insights_parts: list[str] = []

    # Build insights from analysis result keys
    if "cohort_size" in analysis_result:
        insights_parts.append(
            f"The analysis covers {analysis_result['cohort_size']} patients."
        )

    if "group_stats" in analysis_result:
        insights_parts.append("Group-level statistics are available in the analysis result.")

    if "patient_profile" in analysis_result:
        profile = analysis_result["patient_profile"]
        age = profile.get("Age", "not available")
        bmi = profile.get("BMI", "not available")
        insights_parts.append(f"Patient age: {age}, BMI: {bmi}.")

    if "activity_features" in analysis_result:
        af = analysis_result["activity_features"]
        avg = af.get("avg_physical_activity_10d")
        trend = af.get("activity_trend", "not available")
        if avg is not None:
            insights_parts.append(f"Average physical activity level (10-day): {avg:.0f}.")
        insights_parts.append(f"Activity trend: {trend}.")

    if "overall_stats" in analysis_result:
        insights_parts.append("Overall dataset statistics are provided in the analysis result.")

    # Intent-specific recommendations
    if intent == "risk_recommendation":
        recs.append("Discuss these observations with a healthcare professional for personalised guidance.")
    if intent == "comparison":
        recs.append("Review the group differences to identify potential areas of focus.")

    insights = " ".join(insights_parts) if insights_parts else (
        "The structured analysis results are available above."
    )
    return {
        "insights": insights,
        "recommendations": recs,
        "disclaimer": DISCLAIMER,
    }


# ── LLM-based response ──────────────────────────────────────────────
def generate_response(
    question: str,
    intent: str,
    analysis_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate a natural-language response from structured analysis results.

    Uses the LLM when available; falls back to deterministic templates.

    Returns dict with keys: insights, recommendations, disclaimer.
    """
    # No-key mode → deterministic
    if not settings.has_openai_key:
        logger.info("Responder using rule-based mode (no OpenAI key)")
        return _rule_based_response(intent, analysis_result)

    # Build the user message for the LLM
    system = responder_system_prompt()
    safety = safety_rules_text()
    user_msg = (
        f"User question: {question}\n"
        f"Intent: {intent}\n"
        f"Safety rules:\n{safety}\n\n"
        f"Structured analysis result:\n{json.dumps(analysis_result, default=str)}"
    )

    raw = call_llm(system, user_msg)
    if raw is None:
        logger.warning("LLM responder call failed, using rule-based fallback")
        return _rule_based_response(intent, analysis_result)

    # Parse JSON response from LLM
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        result = json.loads(cleaned)
        # Ensure required keys
        return {
            "insights": result.get("insights", ""),
            "recommendations": result.get("recommendations", []),
            "disclaimer": result.get("disclaimer", DISCLAIMER),
        }
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Responder JSON parse failed (%s), using rule-based fallback", exc)
        return _rule_based_response(intent, analysis_result)
