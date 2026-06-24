"""Clinical Co-Pilot — Doctor UI

Run with:
  uv run python ui_app.py
Then open http://localhost:8080
"""

import base64
import json
import os

import google.auth
import uvicorn
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

# ---------------------------------------------------------------------------
# Instructions (same as agents)
# ---------------------------------------------------------------------------
PRESCRIPTION_INSTRUCTION = """You are a clinical prescription reader assistant.

Extract structured medication information from the prescription and return JSON.

FREQUENCY DECODING:
STYLE A (0=dose, -=skip): 0-0=Morning+Night, -0-=Afternoon, 0-0-0=TDS, 0--=Morning, --0=Night
STYLE B (numeric): 1-0-1=Morning+Night, 1-1-1=TDS, 1-0-0=Morning

MEAL TIMING: AC/before food=Before food, PC/after food=After food, before breakfast=Before breakfast,
after breakfast=After breakfast, before lunch=Before lunch, after lunch=After lunch,
before dinner=Before dinner, after dinner=After dinner, HS/bedtime=At bedtime, empty stomach=On empty stomach

Return JSON:
{
  "patient_name": "...", "age": "...", "gender": "...", "visit_date": "...",
  "clinic": "...", "doctor": "...",
  "vitals": {"bp": null, "heart_rate": null, "spo2": null, "temperature": null, "weight": null},
  "clinical_notes": null,
  "medicines": [{
    "name": "...", "dosage": null, "frequency": "raw", "frequency_decoded": "human readable",
    "duration": null, "route": null, "meal_timing": null,
    "quantity_dispensed": null, "special_instructions": null, "flags": []
  }],
  "additional_instructions": null, "flags": [],
  "disclaimer": "AI extraction — doctor must verify before use"
}
Return ONLY valid JSON. Use null for missing fields. Never diagnose."""

NOTES_INSTRUCTION = """You are a clinical notes assistant for a small clinic in India.

The doctor speaks in Telugu/Hindi/English mix. Transcribe and structure into JSON.

Telugu: noppi=pain, jwaram=fever, daggu=cough, tala noppi=headache, aayasam=weakness, vomiting vacchindi=vomiting
Hindi: bukhar=fever, khansi=cough, dard=pain, kamzori=weakness, ulti=vomiting, sar dard=headache

Return JSON:
{
  "patient_name": null, "age": null, "gender": null, "visit_date": null,
  "language_detected": "...",
  "complaints": [], "history": [], "examination_findings": [],
  "diagnosis_impression": null,
  "instructions": [], "follow_up": null,
  "raw_transcript": "...",
  "disclaimer": "AI transcription — doctor must verify before use"
}
Do NOT infer diagnosis. Do NOT add medicine names. Return ONLY valid JSON."""

MESSAGE_INSTRUCTION = """You are a patient communication assistant for a small clinic.

Convert the structured prescription JSON into a WhatsApp-ready patient message.
- Simple language, no jargon
- For each medicine: name, dosage, meal timing (before/after breakfast/lunch/dinner/bedtime), duration
- Include any follow-up from consultation notes if provided
- End with: "If you have any concerns, please call the clinic."
- End with: "⚠️ Please confirm with your doctor before any changes."
- Tone: Warm, simple, reassuring."""

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Clinical Co-Pilot")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html") as f:
        return f.read()


@app.post("/api/prescription/read")
async def read_prescription(file: UploadFile = File(...)):
    ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime = mime_map.get(ext, "image/jpeg")

    image_bytes = await file.read()
    client = genai.Client(vertexai=True, location="global")

    response = client.models.generate_content(
        model=MODEL,
        contents=[types.Content(role="user", parts=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
            types.Part.from_text(text="Extract structured prescription details from this image."),
        ])],
        config=types.GenerateContentConfig(
            system_instruction=PRESCRIPTION_INSTRUCTION,
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    try:
        return JSONResponse(json.loads(response.text))
    except Exception:
        return JSONResponse({"error": "Failed to parse prescription", "raw": response.text})


@app.post("/api/notes/process")
async def process_notes(
    audio: UploadFile = File(None),
    text: str = Form(None),
):
    client = genai.Client(vertexai=True, location="global")

    if audio and audio.filename:
        ext = audio.filename.rsplit(".", 1)[-1].lower()
        mime_map = {"mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4",
                    "ogg": "audio/ogg", "flac": "audio/flac", "aac": "audio/aac", "webm": "audio/webm"}
        mime = mime_map.get(ext, "audio/mpeg")
        audio_bytes = await audio.read()
        parts = [
            types.Part.from_bytes(data=audio_bytes, mime_type=mime),
            types.Part.from_text(text="Transcribe and structure this consultation recording."),
        ]
    elif text:
        parts = [types.Part.from_text(text=f"Structure these consultation notes:\n\n{text}")]
    else:
        return JSONResponse({"error": "Provide either audio file or text"}, status_code=400)

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
        return JSONResponse(json.loads(response.text))
    except Exception:
        return JSONResponse({"error": "Failed to parse notes", "raw": response.text})


@app.post("/api/message/generate")
async def generate_message(
    prescription: str = Form(...),
    notes: str = Form(None),
    patient_name: str = Form(None),
):
    client = genai.Client(vertexai=True, location="global")

    context = f"Prescription data:\n{prescription}"
    if notes:
        context += f"\n\nConsultation notes:\n{notes}"
    if patient_name:
        context += f"\n\nAddress the message to: {patient_name}"

    response = client.models.generate_content(
        model=MODEL,
        contents=[types.Content(role="user", parts=[
            types.Part.from_text(text=f"Generate patient WhatsApp message from:\n\n{context}")
        ])],
        config=types.GenerateContentConfig(
            system_instruction=MESSAGE_INSTRUCTION,
            temperature=0.2,
        ),
    )
    return JSONResponse({"message": response.text})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
