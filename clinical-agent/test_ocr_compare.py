"""Compare OCR quality across models on a prescription image."""

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

INSTRUCTION = """You are a clinical prescription reader assistant.

Your job is to extract structured medication information from a prescription image.
Pay close attention to:
- Circled numbers next to medicine names (these are tablet quantities for dispensing)
- Dashes or digit patterns below medicine names like "-0-", "1-0-1", "0-0-1" (these are frequency/dose timing: morning-afternoon-night)
- Any abbreviations like AC, PC, BD, TDS, OD

For each medicine, extract:
1. Medicine name
2. Dosage
3. Quantity dispensed (circled numbers)
4. Frequency — use X-Y-Z notation: X=morning, Y=afternoon, Z=night
5. Duration
6. Meal timing (AC=before food, PC=after food)
7. Special instructions

Flag unclear fields as ⚠️ UNCLEAR or ⚠️ MISSING.
Output one section per medicine.
⚠️ This is an AI extraction. Doctor must verify before use.
"""

MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3.5-flash",
]


def read_image(path: str):
    ext = path.rsplit(".", 1)[-1].lower()
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime = mime_map.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        return f.read(), mime


def run(image_path: str):
    client = genai.Client(vertexai=True, location="global")
    image_bytes, mime = read_image(image_path)
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)

    for model in MODELS:
        print(f"\n{'=' * 60}")
        print(f"MODEL: {model}")
        print("=" * 60)
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            image_part,
                            types.Part.from_text(text="Extract all medication details from this prescription image."),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=INSTRUCTION,
                    temperature=0.1,
                ),
            )
            print(response.text)
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    image_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/ra20694102/Downloads/Prescription-e1736566887756.jpeg"
    run(image_path)
