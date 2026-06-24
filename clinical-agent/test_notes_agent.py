"""Test the consultation notes agent with an audio file or typed text.

Usage:
  uv run python test_notes_agent.py --audio /path/to/recording.m4a
  uv run python test_notes_agent.py --text "Patient has fever for 2 days..."
"""

import argparse
import json
import os
import sys
import google.auth
from google import genai
from google.genai import types

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

MODEL = "gemini-3.5-flash"

NOTES_INSTRUCTION = """You are a clinical notes assistant for a small general clinic in India.

The doctor speaks naturally during a patient consultation — often mixing Telugu or Hindi
with English medical terms. Your job is to:

1. Transcribe what was said (preserve it in raw_transcript)
2. Structure it into a clean clinical JSON summary

LANGUAGE HANDLING:
- Input may be in Telugu, Hindi, English, or any mix
- Detect and record the language(s) in language_detected (e.g. "Telugu+English")
- Always output the structured fields in English
- Common Telugu medical phrases:
    "noppi" / "nopulu" → pain
    "jwaram" → fever
    "daggu" → cough
    "vomiting vacchindi" → vomiting
    "tala noppi" → headache
    "aayasam" → tiredness/weakness
    "manchi ga undi" → feeling better
- Common Hindi medical phrases:
    "bukhar" → fever | "khansi" → cough | "dard" → pain
    "kamzori" → weakness | "ulti" → vomiting | "sar dard" → headache

OUTPUT FORMAT — return valid JSON with these fields:
{
  "patient_name": "...",
  "age": "...",
  "gender": "...",
  "visit_date": "...",
  "language_detected": "...",
  "complaints": ["..."],
  "history": ["..."],
  "examination_findings": ["..."],
  "diagnosis_impression": "... or null if not stated",
  "instructions": ["..."],
  "follow_up": "... or null",
  "raw_transcript": "full transcription of what was said",
  "disclaimer": "AI transcription — doctor must verify before use"
}

IMPORTANT RULES:
- Do NOT infer diagnosis if the doctor didn't state one — leave null
- Do NOT add medicine names — prescription agent handles that separately
- If the doctor says "this tablet for 5 days" without naming it, note it in
  instructions as-is — medicine names come from the prescription reader
- Return ONLY valid JSON, no markdown, no extra text
"""

AUDIO_MIME_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "webm": "audio/webm",
}


def run_audio(audio_path: str):
    ext = audio_path.rsplit(".", 1)[-1].lower()
    mime = AUDIO_MIME_TYPES.get(ext, "audio/mpeg")

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    client = genai.Client(vertexai=True, location="global")
    print(f"Processing audio: {audio_path} ({mime})")
    print("=" * 60)

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                    types.Part.from_text(
                        text="Transcribe and structure this consultation recording into clinical notes JSON."
                    ),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=NOTES_INSTRUCTION,
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    return response.text


def run_text(text: str):
    client = genai.Client(vertexai=True, location="global")
    print("Processing typed notes...")
    print("=" * 60)

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=f"Structure these consultation notes into clinical notes JSON:\n\n{text}"
                    )
                ],
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=NOTES_INSTRUCTION,
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    return response.text


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audio", help="Path to audio file (mp3, wav, m4a, ogg)")
    group.add_argument("--text", help="Typed consultation notes")
    args = parser.parse_args()

    if args.audio:
        raw = run_audio(args.audio)
    else:
        raw = run_text(args.text)

    try:
        parsed = json.loads(raw)
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(raw)

    print("\n" + "=" * 60)
    print("⚠️  DOCTOR APPROVAL REQUIRED BEFORE USE")
    print("=" * 60)


if __name__ == "__main__":
    main()
