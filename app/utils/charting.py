"""
Charting utilities.

Builds raw chart-ready data payloads for Streamlit to render.
Returns plain dicts/lists — NOT Plotly specs.
Uses unit-neutral labels for all activity-related data.
"""

from typing import Any, Optional


def build_chart_data(
    intent: str,
    analysis_result: dict[str, Any],
    plan: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """
    Build a raw chart-ready payload based on intent and analysis result.

    Returns None if no chart applies.
    """
    if intent == "comparison" and "group_stats" in analysis_result:
        return _comparison_chart(analysis_result["group_stats"], plan)

    if intent == "cohort_analysis" and "overall_stats" in analysis_result:
        return _cohort_chart(analysis_result)

    if intent == "patient_summary" and "activity_features" in analysis_result:
        return _patient_activity_chart(analysis_result["activity_features"])

    if intent == "dataset_summary" and "overall_stats" in analysis_result:
        return _cohort_chart(analysis_result)

    return None


def _comparison_chart(
    group_stats: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Bar-chart-ready data for group comparisons."""
    groups = list(group_stats.keys())
    metrics = plan.get("metrics", [])

    series: dict[str, list] = {m: [] for m in metrics}
    for group in groups:
        for metric in metrics:
            val = group_stats[group].get(metric, {}).get("mean")
            series[metric].append(val)

    return {
        "chart_type": "bar",
        "x_label": ", ".join(plan.get("group_by", ["Group"])),
        "y_label": "Value",
        "categories": groups,
        "series": series,
    }


def _cohort_chart(analysis_result: dict[str, Any]) -> dict[str, Any]:
    """Summary stats chart data."""
    stats = analysis_result.get("overall_stats", {})
    metrics = list(stats.keys())
    means = [stats[m].get("mean") for m in metrics]

    # Use unit-neutral labels
    labels = [m.replace("_", " ").title() for m in metrics]

    return {
        "chart_type": "bar",
        "x_label": "Metric",
        "y_label": "Mean Value",
        "categories": labels,
        "series": {"mean": means},
    }


def _patient_activity_chart(
    activity_features: dict[str, Any],
) -> dict[str, Any]:
    """Activity level overview for a single patient."""
    return {
        "chart_type": "bar",
        "x_label": "Activity Metric",
        "y_label": "Activity Level",
        "categories": [
            "Avg (10d)", "Min (10d)", "Max (10d)",
            "First 3d Avg", "Last 3d Avg",
        ],
        "series": {
            "value": [
                activity_features.get("avg_physical_activity_10d"),
                activity_features.get("min_physical_activity_10d"),
                activity_features.get("max_physical_activity_10d"),
                activity_features.get("first_3d_avg_physical_activity"),
                activity_features.get("last_3d_avg_physical_activity"),
            ]
        },
    }
