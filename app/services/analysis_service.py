"""
Analysis service — the main orchestration layer.

Routes every analysis request through these steps:
1. Validate input & resolve patient_id
2. Get temporary joined data
3. Generate plan (LLM or deterministic)
4. Execute structured analysis (always deterministic)
5. Generate response (LLM narrative or rule-based)
6. Validate output safety (hard-block unsafe LLM text)
7. Return response

The analytics layer ALWAYS produces correct results regardless
of whether an OpenAI key is configured.
"""

import time
from typing import Any, Optional

import pandas as pd

from app.llm.planner import generate_plan, extract_patient_id_from_text
from app.llm.responder import generate_response
from app.llm.validators import validate_and_safe_guard
from app.services.query_service import execute_plan
from app.services.governance_service import sanitize_for_llm, check_input_safety
from app.core.config import settings
from app.core.security import DISCLAIMER, redact_patient_ids
from app.core.metrics import metrics
from app.core.logging_config import logger
from app.utils.charting import build_chart_data


def run_analysis(
    question: str,
    patient_id: Optional[int],
    include_chart: bool,
    df_joined: pd.DataFrame,
) -> dict[str, Any]:
    """
    End-to-end analysis pipeline.

    Args:
        question: The natural-language user question.
        patient_id: Explicit patient ID (overrides NL extraction if conflict).
        include_chart: Whether to include raw chart-ready data.
        df_joined: The temporarily joined DataFrame.

    Returns:
        Dict matching AnalyzeResponse schema.
    """
    start = time.time()
    metrics.record_request()
    metrics.record_analysis()

    # ── 1. Input safety check ────────────────────────────────────────
    is_safe, msg = check_input_safety(question)
    if not is_safe:
        metrics.record_failure()
        return {
            "question": question,
            "intent": "rejected",
            "analysis_result": {},
            "insights": msg,
            "recommendations": [],
            "disclaimer": DISCLAIMER,
            "safety_flags": ["prompt_injection_detected"],
            "latency_ms": int((time.time() - start) * 1000),
            "llm_used": False,
            "chart_data": None,
        }

    # ── 2. Resolve patient_id (explicit wins over NL) ────────────────
    nl_patient_id = extract_patient_id_from_text(question)
    resolved_patient_id = patient_id if patient_id is not None else nl_patient_id

    # ── 3. Generate plan ─────────────────────────────────────────────
    plan = generate_plan(question, resolved_patient_id)
    intent = plan.get("intent", "dataset_summary")

    # ── 4. Execute structured analysis (always deterministic) ────────
    analysis_result = execute_plan(df_joined, plan)

    if "error" in analysis_result:
        metrics.record_failure()
        return {
            "question": question,
            "intent": intent,
            "analysis_result": analysis_result,
            "insights": analysis_result["error"],
            "recommendations": [],
            "disclaimer": DISCLAIMER,
            "safety_flags": [],
            "latency_ms": int((time.time() - start) * 1000),
            "llm_used": False,
            "chart_data": None,
        }

    # ── 5. Generate response (LLM or rule-based) ────────────────────
    #   Sanitize the result before sending to LLM
    sanitized = sanitize_for_llm(analysis_result)
    redacted_question = redact_patient_ids(question)

    resp = generate_response(redacted_question, intent, sanitized)
    llm_used = settings.has_openai_key

    insights = resp.get("insights", "")
    recommendations = resp.get("recommendations", [])

    # ── 6. Safety validation (hard-block unsafe output) ──────────────
    if llm_used:
        insights, recommendations, safety_flags = validate_and_safe_guard(
            insights, recommendations
        )
    else:
        safety_flags = []

    # ── 7. Optional chart data ───────────────────────────────────────
    chart_data = None
    if include_chart:
        chart_data = build_chart_data(intent, analysis_result, plan)

    elapsed_ms = int((time.time() - start) * 1000)
    metrics.record_success()

    logger.info(
        "Analysis complete — intent=%s, llm=%s, latency=%dms, safety_flags=%d",
        intent, llm_used, elapsed_ms, len(safety_flags),
    )

    return {
        "question": question,
        "intent": intent,
        "analysis_result": analysis_result,
        "insights": insights,
        "recommendations": recommendations,
        "disclaimer": DISCLAIMER,
        "safety_flags": safety_flags,
        "latency_ms": elapsed_ms,
        "llm_used": llm_used,
        "chart_data": chart_data,
    }
