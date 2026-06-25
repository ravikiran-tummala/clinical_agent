# ruff: noqa
"""Patient insights generator.

Pulls the full patient history from Firestore, sends it to Gemini,
and writes the result back as a cached insights document.

Called automatically after every save (prescription / consultation / blood report).
"""

import json
import logging
from datetime import datetime, timezone

from google import genai
from google.genai import types

from app import patient_store

logger = logging.getLogger(__name__)

MODEL = "gemini-3.5-flash"

INSIGHTS_INSTRUCTION = """You are a clinical insights analyst for a small general clinic.

You will receive a patient's complete medical history as JSON, including:
- prescriptions (medicines prescribed across visits)
- consultation notes (complaints, diagnosis, instructions across visits)
- blood reports (lab parameters with values, units, and status across visits)

Your job is to generate structured insights a doctor can review before a follow-up visit.

Return JSON matching this exact schema:
{
  "generated_at": "<ISO datetime>",
  "data_summary": "Based on N prescriptions, M consultations, P blood reports",
  "trends": [
    {
      "parameter": "Haemoglobin",
      "direction": "worsening",
      "data_points": [
        {"date": "2025-01-10", "value": "13.2", "unit": "g/dL", "status": "normal"},
        {"date": "2025-03-15", "value": "11.8", "unit": "g/dL", "status": "low"},
        {"date": "2025-06-01", "value": "10.2", "unit": "g/dL", "status": "low"}
      ],
      "observation": "Haemoglobin has been declining steadily over 5 months."
    }
  ],
  "risk_flags": [
    {
      "risk": "Possible developing anaemia",
      "severity": "medium",
      "evidence": "Haemoglobin dropped from 13.2 to 10.2 g/dL across 3 reports despite iron prescription",
      "recommendation_for_doctor": "Consider reviewing iron supplementation compliance and investigating underlying cause"
    }
  ],
  "recurring_patterns": [
    {
      "pattern_type": "complaint",
      "description": "Fever and cough",
      "frequency": "3 of 4 visits"
    },
    {
      "pattern_type": "medication",
      "description": "Paracetamol 500mg",
      "frequency": "every visit"
    }
  ],
  "overall_assessment": "2-4 sentence plain-English paragraph summarising the patient's health trajectory. No diagnosis. No treatment recommendations. Written for the doctor, not the patient.",
  "disclaimer": "AI insights — doctor must verify before acting"
}

RULES:
- Only include trends when there are 2 or more data points for the same parameter
- direction must be one of: "improving", "worsening", "stable", "fluctuating"
- severity must be one of: "low", "medium", "high"
- pattern_type must be one of: "complaint", "medication", "diagnosis"
- If there is only 1 visit/report, set trends=[], risk_flags=[], recurring_patterns=[] and note it in overall_assessment
- Never diagnose
- Never recommend specific medicines or doses
- Base every flag only on data present in the history
- Return ONLY valid JSON
"""


def _build_history_prompt(history: dict) -> str:
    prescriptions = history.get("prescriptions", [])
    consultations = history.get("consultations", [])
    blood_reports = history.get("blood_reports", [])

    parts = [
        f"Patient history for: {history.get('profile', {}).get('name', 'Unknown')}",
        f"Phone: {history.get('profile', {}).get('phone', '')}",
        f"Age/Gender: {history.get('profile', {}).get('age', '?')} / {history.get('profile', {}).get('gender', '?')}",
        "",
        f"--- PRESCRIPTIONS ({len(prescriptions)}) ---",
        json.dumps(prescriptions, default=str, indent=2),
        "",
        f"--- CONSULTATION NOTES ({len(consultations)}) ---",
        json.dumps(consultations, default=str, indent=2),
        "",
        f"--- BLOOD REPORTS ({len(blood_reports)}) ---",
        json.dumps(blood_reports, default=str, indent=2),
    ]
    return "\n".join(parts)


async def generate_and_cache_insights(phone: str) -> dict:
    """Generate insights from full patient history and store in Firestore cache."""
    try:
        history = patient_store.get_patient_history(phone)

        total_records = (
            len(history.get("prescriptions", []))
            + len(history.get("consultations", []))
            + len(history.get("blood_reports", []))
        )
        if total_records == 0:
            logger.info("No records for %s — skipping insights generation", phone)
            return {}

        client = genai.Client(vertexai=True, location="global")
        response = client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=[
                types.Part.from_text(text=_build_history_prompt(history)),
            ])],
            config=types.GenerateContentConfig(
                system_instruction=INSIGHTS_INSTRUCTION,
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )

        insights = json.loads(response.text)
        insights["generated_at"] = datetime.now(timezone.utc).isoformat()
        patient_store.save_insights(phone, insights)
        logger.info("Insights cached for %s", phone)
        return insights

    except Exception:
        logger.exception("Failed to generate insights for %s", phone)
        return {}
