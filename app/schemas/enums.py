"""
Enumerations used across the application.
"""

from enum import Enum


class QueryIntent(str, Enum):
    """Supported analysis intent types."""
    DATASET_SUMMARY = "dataset_summary"
    PATIENT_SUMMARY = "patient_summary"
    COMPARISON = "comparison"
    COHORT_ANALYSIS = "cohort_analysis"
    RISK_RECOMMENDATION = "risk_recommendation"
    TREND_ANALYSIS = "trend_analysis"


class ActivityTrend(str, Enum):
    """Activity trend labels (unit-neutral)."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
