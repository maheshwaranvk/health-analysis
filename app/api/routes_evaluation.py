"""
Evaluation and metrics routes.

POST /api/v1/evaluate   — run predefined evaluation queries
GET  /metrics           — simple metrics summary
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.services.evaluation_service import run_evaluation
from app.core.metrics import metrics

router = APIRouter(tags=["evaluation"])


@router.post("/evaluate")
def evaluate():
    """Run predefined test queries and return a quality report."""
    from app.main import app_state

    if not app_state.datasets_loaded:
        raise HTTPException(status_code=503, detail="Datasets not loaded yet")

    df_joined = app_state.get_joined()
    return run_evaluation(df_joined)


@router.get("/metrics", response_class=PlainTextResponse)
def get_metrics():
    """Return simple Prometheus-style text metrics."""
    m = metrics
    lines = [
        f"# HELP app_requests_total Total API requests",
        f"# TYPE app_requests_total counter",
        f"app_requests_total {m.total_requests}",
        f"",
        f"# HELP app_analysis_requests_total Total analysis requests",
        f"# TYPE app_analysis_requests_total counter",
        f"app_analysis_requests_total {m.analysis_requests}",
        f"",
        f"# HELP app_requests_success Successful requests",
        f"# TYPE app_requests_success counter",
        f"app_requests_success {m.successful_requests}",
        f"",
        f"# HELP app_requests_failed Failed requests",
        f"# TYPE app_requests_failed counter",
        f"app_requests_failed {m.failed_requests}",
        f"",
        f"# HELP app_llm_calls_total LLM call count",
        f"# TYPE app_llm_calls_total counter",
        f"app_llm_calls_total {m.llm_calls}",
        f"",
        f"# HELP app_safety_violations Safety violation count",
        f"# TYPE app_safety_violations counter",
        f"app_safety_violations {m.safety_violations}",
        f"",
        f"# HELP app_avg_latency_ms Average request latency in ms",
        f"# TYPE app_avg_latency_ms gauge",
        f"app_avg_latency_ms {round(m.avg_latency_ms, 2)}",
        f"",
        f"# HELP app_last_latency_ms Last request latency in ms",
        f"# TYPE app_last_latency_ms gauge",
        f"app_last_latency_ms {m.last_latency_ms}",
    ]
    return "\n".join(lines) + "\n"
