# ruff: noqa
from pydantic import BaseModel, Field
from typing import Optional


class Vitals(BaseModel):
    bp: Optional[str] = None
    heart_rate: Optional[str] = None
    spo2: Optional[str] = None
    temperature: Optional[str] = None
    weight: Optional[str] = None


class Medicine(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None          # raw notation e.g. "1-o-1"
    frequency_decoded: Optional[str] = None  # human readable e.g. "Morning and Night"
    duration: Optional[str] = None
    route: Optional[str] = None
    meal_timing: Optional[str] = None
    quantity_dispensed: Optional[str] = None
    special_instructions: Optional[str] = None
    flags: list[str] = Field(default_factory=list)  # unclear/missing fields


class PrescriptionOutput(BaseModel):
    patient_name: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    visit_date: Optional[str] = None
    clinic: Optional[str] = None
    doctor: Optional[str] = None
    vitals: Optional[Vitals] = None
    clinical_notes: Optional[str] = None
    medicines: list[Medicine] = Field(default_factory=list)
    additional_instructions: Optional[str] = None
    flags: list[str] = Field(default_factory=list)
    disclaimer: str = "AI extraction — doctor must verify before use"


class ConsultationNotes(BaseModel):
    patient_name: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    visit_date: Optional[str] = None
    language_detected: Optional[str] = None
    complaints: list[str] = Field(default_factory=list)
    history: list[str] = Field(default_factory=list)
    examination_findings: list[str] = Field(default_factory=list)
    diagnosis_impression: Optional[str] = None
    instructions: list[str] = Field(default_factory=list)
    follow_up: Optional[str] = None
    raw_transcript: Optional[str] = None
    disclaimer: str = "AI transcription — doctor must verify before use"
