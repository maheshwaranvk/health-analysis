"""
Pydantic schemas for API responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class AnalyzeResponse(BaseModel):
    """Response body for POST /api/v1/analyze."""
    question: str
    intent: str
    analysis_result: dict
    insights: str
    recommendations: list[str]
    disclaimer: str
    safety_flags: list[str] = Field(default_factory=list)
    latency_ms: int = 0
    llm_used: bool = False
    chart_data: Optional[dict] = None


class HealthResponse(BaseModel):
    """Response body for GET /health."""
    status: str
    model_configured: bool
    datasets_loaded: bool
    timestamp: str


class DatasetSummaryResponse(BaseModel):
    """Response body for GET /api/v1/dataset/summary."""
    num_patients: int
    num_activity_rows: int
    columns_dataset_1: list[str]
    columns_dataset_2: list[str]
    missing_values_dataset_1: dict
    missing_values_dataset_2: dict


class PatientResponse(BaseModel):
    """Response body for GET /api/v1/patients/{patient_id}."""
    patient_id: int
    profile: dict
    activity_features: dict
    summary: str


class CohortAnalysisResponse(BaseModel):
    """Response body for POST /api/v1/cohort-analysis."""
    filters: list[dict]
    metrics: list[str]
    cohort_size: int
    analysis_result: dict
    narrative: Optional[str] = None
    disclaimer: str
    latency_ms: int = 0
    llm_used: bool = False


class EvaluationResponse(BaseModel):
    """Response body for POST /api/v1/evaluate."""
    total_queries: int
    intent_correct: int
    safety_passed: int
    avg_latency_ms: float
    results: list[dict]
