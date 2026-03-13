"""
Tests for the analysis pipeline.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app, app_state
from app.data.loader import load_dataset_1, load_dataset_2
from app.data.cleaning import clean_dataset_1, clean_dataset_2
from app.data.feature_engineering import compute_activity_features


@pytest.fixture(scope="module", autouse=True)
def _load_datasets():
    """Ensure datasets are loaded before running analysis tests."""
    if not app_state.datasets_loaded:
        raw1 = load_dataset_1()
        raw2 = load_dataset_2()
        app_state.df1_clean, app_state.cleaning_notes_1 = clean_dataset_1(raw1)
        app_state.df2_clean, app_state.cleaning_notes_2 = clean_dataset_2(raw2)
        app_state.activity_features = compute_activity_features(app_state.df2_clean)
        app_state.datasets_loaded = True


client = TestClient(app)


def test_dataset_summary_endpoint():
    response = client.get("/api/v1/dataset/summary")
    assert response.status_code == 200
    data = response.json()
    assert "num_patients" in data
    assert "num_activity_rows" in data
    assert data["num_patients"] > 0


def test_analyze_endpoint_basic():
    response = client.post(
        "/api/v1/analyze",
        json={
            "question": "What is the average BMI?",
            "include_chart": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "intent" in data
    assert "insights" in data
    assert "disclaimer" in data


def test_analyze_with_patient_id():
    response = client.post(
        "/api/v1/analyze",
        json={
            "question": "Show summary for this patient",
            "patient_id": 1,
            "include_chart": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "patient_summary"


def test_patient_lookup_valid():
    response = client.get("/api/v1/patients/1")
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == 1
    assert "profile" in data


def test_patient_lookup_not_found():
    response = client.get("/api/v1/patients/999999")
    assert response.status_code == 404


def test_cohort_analysis_endpoint():
    response = client.post(
        "/api/v1/cohort-analysis",
        json={
            "filters": [{"field": "Smoking", "operator": "==", "value": 1}],
            "metrics": ["BMI", "avg_physical_activity_10d"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "cohort_size" in data
    assert "analysis_result" in data
