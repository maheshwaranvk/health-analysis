"""
Analysis routes.

POST /api/v1/analyze           — main natural-language analysis
POST /api/v1/cohort-analysis   — structured cohort analysis
GET  /api/v1/dataset/summary   — dataset overview
"""

from fastapi import APIRouter, HTTPException

from app.schemas.requests import AnalyzeRequest, CohortAnalysisRequest
from app.schemas.responses import AnalyzeResponse, DatasetSummaryResponse, CohortAnalysisResponse
from app.services.analysis_service import run_analysis
from app.services.query_service import execute_plan, _overall_summary, _apply_filters
from app.llm.responder import generate_response
from app.llm.validators import validate_and_safe_guard
from app.services.governance_service import sanitize_for_llm
from app.core.config import settings
from app.core.security import DISCLAIMER
from app.core.metrics import metrics

import time

router = APIRouter(tags=["analysis"])


# ── Main analysis endpoint ───────────────────────────────────────────
@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    """
    Accept a natural-language question and return structured
    analysis results, insights, recommendations, and optional chart data.
    """
    from app.main import app_state

    if not app_state.datasets_loaded:
        raise HTTPException(status_code=503, detail="Datasets not loaded yet")

    df_joined = app_state.get_joined()
    result = run_analysis(
        question=request.question,
        patient_id=request.patient_id,
        include_chart=request.include_chart,
        df_joined=df_joined,
    )
    return AnalyzeResponse(**result)


# ── Dataset summary endpoint ─────────────────────────────────────────
@router.get("/dataset/summary", response_model=DatasetSummaryResponse)
def dataset_summary():
    """Return high-level statistics about the loaded datasets."""
    from app.main import app_state

    if not app_state.datasets_loaded:
        raise HTTPException(status_code=503, detail="Datasets not loaded yet")

    df1 = app_state.df1_clean
    df2 = app_state.df2_clean

    missing_1 = df1.isnull().sum().to_dict()
    missing_2 = df2.isnull().sum().to_dict()

    return DatasetSummaryResponse(
        num_patients=int(df1["Patient_Number"].nunique()),
        num_activity_rows=len(df2),
        columns_dataset_1=list(df1.columns),
        columns_dataset_2=list(df2.columns),
        missing_values_dataset_1={k: int(v) for k, v in missing_1.items()},
        missing_values_dataset_2={k: int(v) for k, v in missing_2.items()},
    )


# ── Cohort analysis endpoint (structured-first, optional LLM) ───────
@router.post("/cohort-analysis", response_model=CohortAnalysisResponse)
def cohort_analysis(request: CohortAnalysisRequest):
    """
    Structured cohort analysis.
    Deterministic at its core — LLM narrative is optional.
    """
    from app.main import app_state

    if not app_state.datasets_loaded:
        raise HTTPException(status_code=503, detail="Datasets not loaded yet")

    start = time.time()
    metrics.record_request()
    metrics.record_analysis()

    df = app_state.get_joined()

    # Apply filters using deterministic logic
    filters = [f.model_dump() for f in request.filters]
    filtered = _apply_filters(df, filters)

    # Compute metrics
    metrics_cols = request.metrics or ["BMI", "avg_physical_activity_10d", "Blood_Pressure_Abnormality"]
    result = _overall_summary(filtered, metrics_cols)

    # Optional LLM narrative
    narrative = None
    llm_used = False
    if settings.has_openai_key:
        sanitized = sanitize_for_llm(result)
        resp = generate_response(
            f"Cohort analysis with filters {filters}",
            "cohort_analysis",
            sanitized,
        )
        narrative = resp.get("insights", "")
        # Hard-block unsafe output
        narrative, _, safety_flags = validate_and_safe_guard(
            narrative, resp.get("recommendations", [])
        )
        llm_used = True
    else:
        safety_flags = []

    elapsed = int((time.time() - start) * 1000)
    metrics.record_success()

    return CohortAnalysisResponse(
        filters=filters,
        metrics=metrics_cols,
        cohort_size=result.get("cohort_size", 0),
        analysis_result=result,
        narrative=narrative,
        disclaimer=DISCLAIMER,
        latency_ms=elapsed,
        llm_used=llm_used,
    )
