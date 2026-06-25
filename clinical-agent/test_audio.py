"""Quick test: run consultation notes agent on a local audio file."""
import json
import os
import sys

from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash"

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

audio_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/ra20694102/Downloads/New Recording 31_2918.m4a"

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    sys.exit("Set GOOGLE_API_KEY first: export GOOGLE_API_KEY=your-key")
client = genai.Client(api_key=api_key)

print(f"Uploading audio: {audio_path}")
uploaded = client.files.upload(
    file=audio_path,
    config={"mime_type": "audio/mp4"},
)
print(f"Uploaded: {uploaded.name} ({uploaded.size_bytes:,} bytes)")

print(f"Sending to {MODEL} ...")
response = client.models.generate_content(
    model=MODEL,
    contents=[types.Content(role="user", parts=[
        types.Part.from_uri(file_uri=uploaded.uri, mime_type="audio/mp4"),
        types.Part.from_text(text="Transcribe and structure this consultation recording."),
    ])],
    config=types.GenerateContentConfig(
        system_instruction=NOTES_INSTRUCTION,
        temperature=0.1,
        response_mime_type="application/json",
    ),
)

print("\n=== RAW RESPONSE ===")
print(response.text)

try:
    parsed = json.loads(response.text)
    print("\n=== PARSED JSON ===")
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"\nJSON parse error: {e}")
