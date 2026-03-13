"""
Pydantic schemas for API requests.
"""

from pydantic import BaseModel, Field
from typing import Optional


class AnalyzeRequest(BaseModel):
    """Request body for POST /api/v1/analyze."""
    question: str = Field(..., min_length=3, max_length=1000, description="Natural language question")
    patient_id: Optional[int] = Field(None, description="Explicit patient ID (overrides NL extraction)")
    include_chart: bool = Field(False, description="Include chart-ready data in response")


class CohortFilter(BaseModel):
    """A single filter clause for cohort analysis."""
    field: str
    operator: str
    value: object


class CohortAnalysisRequest(BaseModel):
    """Request body for POST /api/v1/cohort-analysis."""
    filters: list[CohortFilter] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=lambda: ["BMI", "avg_physical_activity_10d", "Blood_Pressure_Abnormality"])
