# ruff: noqa
"""Firestore-backed patient history store.

Collection structure:
  patients/{phone}/profile          — PatientProfile dict
  patients/{phone}/prescriptions    — {doc_id}: PrescriptionOutput dict + saved_at
  patients/{phone}/consultations    — {doc_id}: ConsultationNotes dict + saved_at
  patients/{phone}/blood_reports    — {doc_id}: BloodReport + BloodReportSummary dicts + saved_at

Phone number is used as the patient identifier (matches WhatsApp ID).
"""

from datetime import datetime, timezone
from typing import Optional

from google.cloud import firestore

_db: Optional[firestore.Client] = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client()
    return _db


def _patient_ref(phone: str) -> firestore.DocumentReference:
    return _get_db().collection("patients").document(phone)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

def upsert_patient_profile(phone: str, name: str = None, age: str = None, gender: str = None) -> dict:
    """Create or update basic patient profile."""
    ref = _patient_ref(phone)
    data = {"phone": phone, "updated_at": datetime.now(timezone.utc)}
    if name:
        data["name"] = name
    if age:
        data["age"] = age
    if gender:
        data["gender"] = gender
    ref.set(data, merge=True)
    return data


def get_patient_profile(phone: str) -> Optional[dict]:
    doc = _patient_ref(phone).get()
    return doc.to_dict() if doc.exists else None


# ---------------------------------------------------------------------------
# Prescriptions
# ---------------------------------------------------------------------------

def save_prescription(phone: str, prescription: dict) -> str:
    """Save a doctor-approved prescription. Returns the new document ID."""
    upsert_patient_profile(
        phone,
        name=prescription.get("patient_name"),
        age=prescription.get("age"),
        gender=prescription.get("gender"),
    )
    ref = _patient_ref(phone).collection("prescriptions").document()
    ref.set({**prescription, "saved_at": datetime.now(timezone.utc)})
    return ref.id


def get_prescriptions(phone: str) -> list[dict]:
    docs = _patient_ref(phone).collection("prescriptions").order_by(
        "saved_at", direction=firestore.Query.DESCENDING
    ).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


# ---------------------------------------------------------------------------
# Consultation Notes
# ---------------------------------------------------------------------------

def save_consultation(phone: str, notes: dict) -> str:
    """Save doctor-approved consultation notes. Returns the new document ID."""
    upsert_patient_profile(
        phone,
        name=notes.get("patient_name"),
        age=notes.get("age"),
        gender=notes.get("gender"),
    )
    ref = _patient_ref(phone).collection("consultations").document()
    ref.set({**notes, "saved_at": datetime.now(timezone.utc)})
    return ref.id


def get_consultations(phone: str) -> list[dict]:
    docs = _patient_ref(phone).collection("consultations").order_by(
        "saved_at", direction=firestore.Query.DESCENDING
    ).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


# ---------------------------------------------------------------------------
# Blood Reports
# ---------------------------------------------------------------------------

def save_blood_report(phone: str, report: dict, summary: dict) -> str:
    """Save a doctor-approved blood report + its summary. Returns the new document ID."""
    upsert_patient_profile(
        phone,
        name=report.get("patient_name"),
        age=report.get("age"),
        gender=report.get("gender"),
    )
    ref = _patient_ref(phone).collection("blood_reports").document()
    ref.set({
        "report": report,
        "summary": summary,
        "saved_at": datetime.now(timezone.utc),
    })
    return ref.id


def get_blood_reports(phone: str) -> list[dict]:
    docs = _patient_ref(phone).collection("blood_reports").order_by(
        "saved_at", direction=firestore.Query.DESCENDING
    ).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


# ---------------------------------------------------------------------------
# Full patient history
# ---------------------------------------------------------------------------

def get_patient_history(phone: str) -> dict:
    """Return complete patient history across all record types."""
    return {
        "profile": get_patient_profile(phone),
        "prescriptions": get_prescriptions(phone),
        "consultations": get_consultations(phone),
        "blood_reports": get_blood_reports(phone),
    }
