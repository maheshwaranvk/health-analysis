"""
Evaluation service.

Runs predefined test queries through the pipeline and reports
correctness, safety, and latency scores.
"""

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from app.services.analysis_service import run_analysis
from app.core.config import BASE_DIR
from app.core.security import DISCLAIMER
from app.core.logging_config import logger


def load_evaluation_queries() -> list[dict[str, Any]]:
    """Load evaluation queries from evaluation_queries.json."""
    path = BASE_DIR / "evaluation_queries.json"
    if not path.exists():
        logger.warning("evaluation_queries.json not found at %s", path)
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_evaluation(df_joined: pd.DataFrame) -> dict[str, Any]:
    """
    Execute all evaluation queries and return a summary report.
    """
    queries = load_evaluation_queries()
    if not queries:
        return {"total_queries": 0, "error": "No evaluation queries found"}

    results: list[dict[str, Any]] = []
    total_latency = 0.0
    intent_correct = 0
    safety_passed = 0

    for q in queries:
        question = q.get("question", "")
        expected_intent = q.get("expected_intent")

        response = run_analysis(
            question=question,
            patient_id=q.get("patient_id"),
            include_chart=False,
            df_joined=df_joined,
        )

        latency = response.get("latency_ms", 0)
        total_latency += latency

        # Check intent correctness
        actual_intent = response.get("intent", "")
        intent_match = actual_intent == expected_intent if expected_intent else True
        if intent_match:
            intent_correct += 1

        # Check safety (no safety flags and disclaimer present)
        has_disclaimer = DISCLAIMER in response.get("disclaimer", "")
        no_violations = len(response.get("safety_flags", [])) == 0
        is_safe = has_disclaimer and no_violations
        if is_safe:
            safety_passed += 1

        results.append({
            "question": question,
            "expected_intent": expected_intent,
            "actual_intent": actual_intent,
            "intent_correct": intent_match,
            "safety_passed": is_safe,
            "latency_ms": latency,
            "safety_flags": response.get("safety_flags", []),
        })

    total = len(queries)
    return {
        "total_queries": total,
        "intent_correct": intent_correct,
        "safety_passed": safety_passed,
        "avg_latency_ms": round(total_latency / total, 2) if total > 0 else 0,
        "results": results,
    }
