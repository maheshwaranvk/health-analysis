"""
Patient routes.

GET /api/v1/patients/{patient_id}
"""

from fastapi import APIRouter, HTTPException

from app.schemas.responses import PatientResponse
from app.services.patient_service import get_patient_summary

router = APIRouter(tags=["patients"])


@router.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: int):
    """Return profile, activity features, and a brief summary for one patient."""
    from app.main import app_state

    if not app_state.datasets_loaded:
        raise HTTPException(status_code=503, detail="Datasets not loaded yet")

    df_joined = app_state.get_joined()
    result = get_patient_summary(df_joined, patient_id)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    return PatientResponse(**result)
