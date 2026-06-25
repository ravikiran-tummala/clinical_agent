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


class BloodParameter(BaseModel):
    name: str
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: Optional[str] = None          # "normal", "high", "low", "critical"
    flags: list[str] = Field(default_factory=list)


class BloodReport(BaseModel):
    patient_name: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    report_date: Optional[str] = None
    lab_name: Optional[str] = None
    doctor_name: Optional[str] = None
    parameters: list[BloodParameter] = Field(default_factory=list)
    overall_flags: list[str] = Field(default_factory=list)
    disclaimer: str = "AI extraction — doctor must verify before use"


class BloodReportSummary(BaseModel):
    patient_name: Optional[str] = None
    report_date: Optional[str] = None
    normal_count: int = 0
    abnormal_count: int = 0
    critical_count: int = 0
    key_findings: list[str] = Field(default_factory=list)
    watch_list: list[str] = Field(default_factory=list)
    questions_for_doctor: list[str] = Field(default_factory=list)
    plain_summary: str = ""
    disclaimer: str = "AI summary — doctor must verify before use"


# ---------------------------------------------------------------------------
# Patient Insights
# ---------------------------------------------------------------------------

class TrendPoint(BaseModel):
    date: Optional[str] = None
    value: str
    unit: Optional[str] = None
    status: Optional[str] = None  # "normal", "low", "high", "critical"


class ParameterTrend(BaseModel):
    parameter: str
    direction: str  # "improving", "worsening", "stable", "fluctuating"
    data_points: list[TrendPoint] = Field(default_factory=list)
    observation: str  # one-line human-readable summary


class RiskFlag(BaseModel):
    risk: str
    severity: str  # "low", "medium", "high"
    evidence: str  # which data points support this
    recommendation_for_doctor: str


class RecurringPattern(BaseModel):
    pattern_type: str  # "complaint", "medication", "diagnosis"
    description: str
    frequency: str  # e.g. "3 of 4 visits", "every visit"


class PatientInsights(BaseModel):
    generated_at: Optional[str] = None
    data_summary: str = ""  # e.g. "Based on 3 prescriptions, 2 consultations, 1 blood report"
    trends: list[ParameterTrend] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    recurring_patterns: list[RecurringPattern] = Field(default_factory=list)
    overall_assessment: str = ""  # plain-English paragraph for the doctor
    disclaimer: str = "AI insights — doctor must verify before acting"
