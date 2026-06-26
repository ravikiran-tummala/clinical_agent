# ruff: noqa
"""Firestore-backed patient history store.

Collection structure:
  patients/{phone}/profile          — PatientProfile dict
  patients/{phone}/prescriptions    — {doc_id}: PrescriptionOutput dict + saved_at
  patients/{phone}/consultations    — {doc_id}: ConsultationNotes dict + saved_at + follow_up_date
  patients/{phone}/blood_reports    — {doc_id}: BloodReport + BloodReportSummary dicts + saved_at
  followups/{id}                    — denormalised follow-up index for fast dashboard queries

Phone number is used as the patient identifier (matches WhatsApp ID).
"""

import re
from datetime import date, datetime, timedelta, timezone
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

def parse_follow_up_days(text: str) -> int:
    """Parse follow_up text into a number of days. Falls back to 3."""
    if not text:
        return 3
    t = text.lower()
    m = re.search(r'(\d+)\s*month', t)
    if m:
        return int(m.group(1)) * 30
    m = re.search(r'(\d+)\s*week', t)
    if m:
        return int(m.group(1)) * 7
    m = re.search(r'(\d+)\s*day', t)
    if m:
        return int(m.group(1))
    return 3


def save_consultation(phone: str, notes: dict, patient_name: str = None) -> str:
    """Save doctor-approved consultation notes. Returns the new document ID."""
    upsert_patient_profile(
        phone,
        name=notes.get("patient_name") or patient_name,
        age=notes.get("age"),
        gender=notes.get("gender"),
    )
    saved_at = datetime.now(timezone.utc)
    ref = _patient_ref(phone).collection("consultations").document()

    follow_up_text = notes.get("follow_up")
    follow_up_date = None
    if follow_up_text:
        days = parse_follow_up_days(follow_up_text)
        follow_up_date = (saved_at + timedelta(days=days)).date().isoformat()

    ref.set({**notes, "saved_at": saved_at, "follow_up_date": follow_up_date})

    # Write denormalised follow-up index entry for dashboard queries
    if follow_up_date:
        profile = get_patient_profile(phone)
        _get_db().collection("followups").document(f"{phone}_{ref.id}").set({
            "phone": phone,
            "patient_name": profile.get("name") if profile else (notes.get("patient_name") or patient_name or phone),
            "follow_up_date": follow_up_date,
            "follow_up_text": follow_up_text,
            "consultation_id": ref.id,
            "saved_at": saved_at,
            "dismissed": False,
        })

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
# Insights cache
# ---------------------------------------------------------------------------

def save_insights(phone: str, insights: dict) -> None:
    """Overwrite the cached insights document for this patient."""
    _patient_ref(phone).collection("insights").document("latest").set(insights)


def get_insights(phone: str) -> Optional[dict]:
    """Return cached insights, or None if not yet generated."""
    doc = _patient_ref(phone).collection("insights").document("latest").get()
    return doc.to_dict() if doc.exists else None


# ---------------------------------------------------------------------------
# Follow-up reminders
# ---------------------------------------------------------------------------

def get_due_followups(as_of: date = None) -> list[dict]:
    """Return all undismissed follow-ups due on or before as_of (defaults to today)."""
    cutoff = (as_of or date.today()).isoformat()
    docs = (
        _get_db()
        .collection("followups")
        .where("dismissed", "==", False)
        .where("follow_up_date", "<=", cutoff)
        .order_by("follow_up_date")
        .stream()
    )
    results = []
    for d in docs:
        entry = {"id": d.id, **d.to_dict()}
        # saved_at is a Firestore Timestamp — serialise to ISO string
        if hasattr(entry.get("saved_at"), "isoformat"):
            entry["saved_at"] = entry["saved_at"].isoformat()
        results.append(entry)
    return results


def dismiss_followup(followup_id: str) -> None:
    """Mark a follow-up reminder as dismissed."""
    _get_db().collection("followups").document(followup_id).update({"dismissed": True})


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
