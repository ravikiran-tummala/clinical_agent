"""Quick test: run a prescription image through the reader + message creator agents."""

import sys
import base64
import os
import google.auth
from google import genai
from google.genai import types

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

PRESCRIPTION_READER_INSTRUCTION = """You are a clinical prescription reader assistant.

Your job is to extract structured medication information from a prescription image.

For each medicine, extract these fields:
1. Medicine name (generic or brand)
2. Dosage (e.g., 500 mg, 10 ml)
3. Frequency — decode using the FREQUENCY rules below
4. Duration (e.g., 5 days, 1 week, until reviewed)
5. Route (e.g., oral, topical) — if mentioned
6. Meal timing — decode using the MEAL TIMING rules below
7. Special instructions (e.g., avoid alcohol, take with water)
8. Condition/indication — if mentioned

Also extract any patient vitals or clinical notes visible on the prescription
(BP, HR, SpO2, Temp, weight, diagnosis notes).

---
FREQUENCY DECODING RULES:

Dash-zero notation (very common in Indian clinics):
  There are TWO notation styles doctors use — read carefully:

  STYLE A — "0 means take a dose, - means skip":
    Positions are: Morning - Afternoon - Night
    0   = take one dose at this time slot
    -   = skip / no dose at this time slot
    Examples:
      0-0    → Morning and Night (afternoon skipped — only 2 slots written)
      -0-    → Afternoon only
      0-0-0  → Morning, Afternoon, Night (three times daily)
      0--    → Morning only
      --0    → Night only
      0-0-   → Morning and Afternoon

  STYLE B — numeric count per slot (X-Y-Z):
    1-0-1  → 1 tablet morning, 0 afternoon, 1 night
    1-1-1  → 1 tablet morning, afternoon, night
    2-0-2  → 2 tablets morning, 0 afternoon, 2 night
    0-0-1  → Night only
    1-0-0  → Morning only

  When you see a mix of 0s and dashes, use STYLE A.
  When you see numbers greater than 1, use STYLE B.

Standard abbreviations:
  OD/QD → once daily | BD/BID → twice daily | TDS/TID → three times daily
  QID → four times daily | SOS → as needed | HS → at bedtime | Q8H → every 8 hours

---
MEAL TIMING DECODING RULES:

  AC / a.c. / "before food" / "bf"      → Before food
  PC / p.c. / "after food" / "af"       → After food
  CC / c.c. / "with food"               → With food
  "empty stomach" / "fasting"           → On empty stomach
  "before breakfast" / "BB"             → Before breakfast
  "after breakfast"                     → After breakfast
  "before lunch"                        → Before lunch
  "after lunch"                         → After lunch
  "before dinner"                       → Before dinner
  "after dinner"                        → After dinner
  "at night" / "at bedtime" / "HS"      → At bedtime

If meal timing is not stated: ⚠️ MISSING (meal timing not specified — doctor to clarify)

---

OUTPUT FORMAT — return valid JSON with this structure:
{
  "patient_name": "...",
  "age": "...",
  "gender": "...",
  "visit_date": "...",
  "clinic": "...",
  "doctor": "...",
  "vitals": {"bp": "...", "heart_rate": "...", "spo2": "...", "temperature": "...", "weight": "..."},
  "clinical_notes": "...",
  "medicines": [
    {
      "name": "...",
      "dosage": "...",
      "frequency": "raw notation e.g. 1-o-1",
      "frequency_decoded": "human readable e.g. Morning and Night",
      "duration": "...",
      "route": "...",
      "meal_timing": "...",
      "quantity_dispensed": "...",
      "special_instructions": "...",
      "flags": ["list any unclear or missing fields"]
    }
  ],
  "additional_instructions": "...",
  "flags": ["prescription-level flags"],
  "disclaimer": "AI extraction — doctor must verify before use"
}

Use null for missing fields. Return ONLY valid JSON, no markdown, no extra text.

SAFETY RULES:
- Never diagnose
- Never recommend treatment changes
- Flag ambiguous abbreviations
"""

MESSAGE_CREATOR_INSTRUCTION = """You are a patient communication assistant for a small clinic.

You will receive a structured prescription summary. Convert it into a clear,
friendly, patient-readable medication instruction message for WhatsApp.

Guidelines:
- Use simple, everyday language — avoid medical jargon
- Format for WhatsApp (short paragraphs, use emojis sparingly but helpfully)
- Include for each medicine:
  * What to take (medicine name)
  * How much (dosage)
  * When to take it — be specific about meal timing:
      - "Before breakfast" / "After breakfast"
      - "Before lunch" / "After lunch" / "With lunch"
      - "Before dinner" / "After dinner" / "With dinner"
      - "At bedtime" (for night-only medicines)
      - "On empty stomach" (if explicitly stated)
      - If no meal instruction given, use: morning / afternoon / evening / night
  * How long (number of days)
  * Any special instructions
- End with: "If you have any concerns, please call the clinic."

IMPORTANT SAFETY RULES:
- Never add medicines not in the prescription
- Never suggest dosage changes
- Never provide medical advice beyond what the doctor prescribed
- Always end with: "⚠️ Please confirm with your doctor before any changes."

Tone: Warm, simple, reassuring.
"""


def read_image_as_base64(path: str) -> tuple[str, str]:
    ext = path.rsplit(".", 1)[-1].lower()
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime = mime_map.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode(), mime


def run(image_path: str):
    client = genai.Client(vertexai=True, location="global")
    model = "gemini-3.5-flash"

    b64, mime = read_image_as_base64(image_path)
    image_part = types.Part.from_bytes(data=base64.b64decode(b64), mime_type=mime)

    print("=" * 60)
    print("STEP 1: PRESCRIPTION READER AGENT")
    print("=" * 60)

    reader_response = client.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=[
                    image_part,
                    types.Part.from_text(text="Please extract the structured prescription details from this image."),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=PRESCRIPTION_READER_INSTRUCTION,
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    structured_prescription = reader_response.text
    try:
        import json
        parsed = json.loads(structured_prescription)
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except Exception:
        print(structured_prescription)

    print("\n" + "=" * 60)
    print("STEP 2: MESSAGE CREATOR AGENT")
    print("=" * 60)

    message_response = client.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=f"Here is the structured prescription:\n\n{structured_prescription}\n\n"
                        "Please generate a patient-friendly WhatsApp medication message."
                    )
                ],
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=MESSAGE_CREATOR_INSTRUCTION,
            temperature=0.2,
        ),
    )
    print(message_response.text)
    print("\n" + "=" * 60)
    print("⚠️  DOCTOR APPROVAL REQUIRED BEFORE SHARING WITH PATIENT")
    print("=" * 60)


if __name__ == "__main__":
    image_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/ra20694102/Downloads/1.webp"
    run(image_path)
