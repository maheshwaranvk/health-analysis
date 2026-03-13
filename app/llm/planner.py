"""
Planner module.

Converts a natural-language user question into a structured JSON plan
using the LLM planner prompt (when OpenAI is available) or deterministic
regex-based fallback (no-key mode / planner failure).
"""

import json
import re
from typing import Any, Optional

from app.llm.client import call_llm
from app.llm.prompts import planner_system_prompt
from app.core.config import settings
from app.core.logging_config import logger

# ── Allowed fields for validation ────────────────────────────────────
ALLOWED_FIELDS: set[str] = {
    "Blood_Pressure_Abnormality", "Level_of_Hemoglobin",
    "Genetic_Pedigree_Coefficient", "Age", "BMI", "Sex", "Pregnancy",
    "Smoking", "salt_content_in_the_diet", "alcohol_consumption_per_day",
    "Level_of_Stress", "Chronic_kidney_disease", "Adrenal_and_thyroid_disorders",
    "avg_physical_activity_10d", "min_physical_activity_10d",
    "max_physical_activity_10d", "std_physical_activity_10d",
    "days_with_missing_activity", "activity_trend",
}

ALLOWED_OPERATORS: set[str] = {"==", "!=", ">", ">=", "<", "<=", "in"}

ALLOWED_INTENTS: set[str] = {
    "dataset_summary", "patient_summary", "comparison",
    "cohort_analysis", "risk_recommendation", "trend_analysis",
}


# ── Regex-based patient ID extraction ────────────────────────────────
_PATIENT_RE = re.compile(r"patient\s*(?:#|number|id|no\.?)?\s*(\d+)", re.IGNORECASE)


def extract_patient_id_from_text(text: str) -> Optional[int]:
    """Extract a patient ID from free text using regex. Returns None if not found."""
    m = _PATIENT_RE.search(text)
    return int(m.group(1)) if m else None


# ── Regex-based intent detection (no-key fallback) ───────────────────
_INTENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("patient_summary", re.compile(r"patient\s*(?:#|number|id|no\.?)?\s*\d+", re.IGNORECASE)),
    ("comparison", re.compile(r"\b(compare|vs|versus|difference)\b", re.IGNORECASE)),
    ("trend_analysis", re.compile(r"\b(trend|over\s+time|change)\b", re.IGNORECASE)),
    ("risk_recommendation", re.compile(r"\b(recommend|risk|advice|suggest)\b", re.IGNORECASE)),
    ("cohort_analysis", re.compile(r"\b(cohort|group|filter|subset)\b", re.IGNORECASE)),
    ("dataset_summary", re.compile(r"\b(summary|overview|dataset|statistics)\b", re.IGNORECASE)),
]


def detect_intent_regex(question: str) -> str:
    """Deterministic intent detection using regex patterns."""
    for intent, pattern in _INTENT_PATTERNS:
        if pattern.search(question):
            return intent
    return "dataset_summary"


# ── Plan validation ──────────────────────────────────────────────────
def _validate_plan(plan: dict[str, Any]) -> bool:
    """Return True if the plan has valid structure and allowed values."""
    intent = plan.get("intent")
    if intent not in ALLOWED_INTENTS:
        return False

    for f in plan.get("filters", []):
        if f.get("field") not in ALLOWED_FIELDS:
            return False
        if f.get("operator") not in ALLOWED_OPERATORS:
            return False

    for m in plan.get("metrics", []):
        if m not in ALLOWED_FIELDS:
            return False

    for g in plan.get("group_by", []):
        if g not in ALLOWED_FIELDS:
            return False

    return True


# ── Deterministic fallback plan ──────────────────────────────────────
def _deterministic_plan(
    question: str,
    explicit_patient_id: Optional[int],
) -> dict[str, Any]:
    """Build a plan without the LLM using regex intent detection."""
    # Resolve patient ID: explicit field wins
    nl_patient_id = extract_patient_id_from_text(question)
    patient_id = explicit_patient_id if explicit_patient_id is not None else nl_patient_id

    if patient_id is not None:
        return {
            "intent": "patient_summary",
            "patient_id": patient_id,
            "filters": [],
            "group_by": [],
            "metrics": [],
            "analysis_type": "patient_detail",
        }

    intent = detect_intent_regex(question)
    return {
        "intent": intent,
        "patient_id": None,
        "filters": [],
        "group_by": [],
        "metrics": ["BMI", "avg_physical_activity_10d", "Blood_Pressure_Abnormality"],
        "analysis_type": "overall_summary",
    }


# ── Main planner entry point ────────────────────────────────────────
def generate_plan(
    question: str,
    explicit_patient_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Generate a structured analysis plan from a user question.

    Uses the LLM planner when available, with deterministic fallback.
    The explicit patient_id always wins over NL extraction if both conflict.
    """
    # Always extract via regex first (deterministic, no LLM needed)
    nl_patient_id = extract_patient_id_from_text(question)
    resolved_patient_id = (
        explicit_patient_id if explicit_patient_id is not None else nl_patient_id
    )

    # Try LLM planner if key is available
    if settings.has_openai_key:
        system = planner_system_prompt()
        user_msg = f"Question: {question}"
        if resolved_patient_id is not None:
            user_msg += f"\nPatient ID: {resolved_patient_id}"

        raw = call_llm(system, user_msg)
        if raw:
            try:
                # Strip markdown fences if present
                cleaned = raw.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                    cleaned = re.sub(r"\s*```$", "", cleaned)
                plan = json.loads(cleaned)
                if _validate_plan(plan):
                    # Override patient_id with resolved value
                    plan["patient_id"] = resolved_patient_id
                    logger.info("LLM planner succeeded — intent: %s", plan.get("intent"))
                    return plan
                else:
                    logger.warning("LLM planner returned invalid plan, falling back")
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("LLM planner JSON parse failed (%s), falling back", exc)

    # Deterministic fallback
    plan = _deterministic_plan(question, resolved_patient_id)
    logger.info("Using deterministic plan — intent: %s", plan.get("intent"))
    return plan
