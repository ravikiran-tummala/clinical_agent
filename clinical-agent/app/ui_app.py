# ruff: noqa
"""
Clinical Co-Pilot UI — FastAPI backend for the doctor-facing web app.

Screens:
  1. Patient selection (phone number)
  2. Voice recording → consultation notes
  3. Prescription upload → structured summary + WhatsApp message
"""

import base64
import json
import os

import google.auth
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

MODEL = "gemini-3.5-flash"

app = FastAPI(title="Clinical Co-Pilot")
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# ---------------------------------------------------------------------------
# Gemini instructions (same as agents)
# ---------------------------------------------------------------------------

PRESCRIPTION_INSTRUCTION = """You are a clinical prescription reader assistant.
Extract structured medication information from the prescription image and return JSON.

FREQUENCY DECODING:
STYLE A (0=dose, -=skip): 0-0=Morning+Night, -0-=Afternoon, 0-0-0=All three, 0--=Morning, --0=Night
STYLE B (numeric): 1-0-1=Morning+Night, 1-1-1=Three times, 0-0-1=Night only
Standard: OD=once, BD=twice, TDS=three times, HS=bedtime

MEAL TIMING: AC/before food→Before food, PC/after food→After food, empty stomach→On empty stomach,
before/after breakfast/lunch/dinner as written. HS/at night→At bedtime.

Return JSON only:
{
  "patient_name": null, "age": null, "gender": null, "visit_date": null,
  "clinic": null, "doctor": null,
  "vitals": {"bp": null, "heart_rate": null, "spo2": null, "temperature": null, "weight": null},
  "clinical_notes": null,
  "medicines": [{
    "name": "...", "dosage": null, "frequency": null, "frequency_decoded": null,
    "duration": null, "route": null, "meal_timing": null,
    "quantity_dispensed": null, "special_instructions": null, "flags": []
  }],
  "additional_instructions": null,
  "flags": [],
  "disclaimer": "AI extraction — doctor must verify before use"
}
Use null for missing. Return ONLY valid JSON."""

MESSAGE_INSTRUCTION = """You are a patient communication assistant for a clinic.
Convert the structured prescription JSON into a WhatsApp-ready patient message.
- Simple language, no jargon
- Specific meal timing: before/after breakfast, lunch, dinner, at bedtime, on empty stomach
- Include follow-up if present
- End with: "If you have any concerns, please call the clinic."
- End with: "⚠️ Please confirm with your doctor before any changes."
Tone: Warm, simple, reassuring. Return plain text only."""

NOTES_INSTRUCTION = """You are a clinical notes assistant for a clinic in India.
The doctor may speak in Telugu, Hindi, English or a mix.
Transcribe and structure into JSON. Map regional terms to English.
Telugu: jwaram=fever, daggu=cough, tala noppi=headache, noppi=pain, aayasam=weakness
Hindi: bukhar=fever, khansi=cough, dard=pain, kamzori=weakness, ulti=vomiting

Return JSON only:
{
  "patient_name": null, "age": null, "gender": null, "visit_date": null,
  "language_detected": null,
  "complaints": [], "history": [], "examination_findings": [],
  "diagnosis_impression": null, "instructions": [], "follow_up": null,
  "raw_transcript": null,
  "disclaimer": "AI transcription — doctor must verify before use"
}
Do NOT infer diagnosis. Do NOT add medicine names. Return ONLY valid JSON."""


def get_client():
    return genai.Client(vertexai=True, location="global")


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(os.path.dirname(__file__), "static", "index.html")) as f:
        return f.read()


@app.post("/api/analyze-prescription")
async def analyze_prescription(file: UploadFile = File(...)):
    image_bytes = await file.read()
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime = mime_map.get(ext, "image/jpeg")

    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=[types.Content(role="user", parts=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
            types.Part.from_text(text="Extract all prescription details."),
        ])],
        config=types.GenerateContentConfig(
            system_instruction=PRESCRIPTION_INSTRUCTION,
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    try:
        prescription = json.loads(response.text)
    except Exception:
        return JSONResponse({"error": "Could not parse prescription"}, status_code=500)

    # Generate WhatsApp message
    msg_response = client.models.generate_content(
        model=MODEL,
        contents=[types.Content(role="user", parts=[
            types.Part.from_text(text=f"Prescription JSON:\n{json.dumps(prescription)}\n\nGenerate patient WhatsApp message.")
        ])],
        config=types.GenerateContentConfig(
            system_instruction=MESSAGE_INSTRUCTION,
            temperature=0.2,
        ),
    )

    return JSONResponse({
        "prescription": prescription,
        "message": msg_response.text,
    })


@app.post("/api/analyze-notes")
async def analyze_notes(
    audio: UploadFile = File(None),
    text: str = Form(None),
):
    client = get_client()

    if audio:
        audio_bytes = await audio.read()
        ext = (audio.filename or "").rsplit(".", 1)[-1].lower()
        audio_mime = {
            "mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4",
            "ogg": "audio/ogg", "webm": "audio/webm", "aac": "audio/aac",
        }.get(ext, "audio/mpeg")
        parts = [
            types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime),
            types.Part.from_text(text="Transcribe and structure this consultation recording."),
        ]
    elif text:
        parts = [types.Part.from_text(text=f"Structure these consultation notes:\n\n{text}")]
    else:
        return JSONResponse({"error": "Provide audio or text"}, status_code=400)

    response = client.models.generate_content(
        model=MODEL,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            system_instruction=NOTES_INSTRUCTION,
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    try:
        notes = json.loads(response.text)
    except Exception:
        return JSONResponse({"error": "Could not parse notes"}, status_code=500)

    return JSONResponse({"notes": notes})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
