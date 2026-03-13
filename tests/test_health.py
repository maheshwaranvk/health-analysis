"""
Tests for the health endpoint.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "datasets_loaded" in data


def test_health_model_configured_flag():
    response = client.get("/health")
    data = response.json()
    assert isinstance(data["model_configured"], bool)
