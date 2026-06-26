# 🩺 Clinical Co-Pilot — Agentic AI Assistant for Small Clinics

An AI-powered clinical assistant built for small general clinics in India. It reduces the doctor's cognitive load by structuring handwritten prescriptions, transcribing consultation audio, analysing blood reports, and maintaining a persistent patient history — while keeping the doctor fully in control of every decision.

> **This is a clinical decision support tool, not a medical device.**
> All outputs require doctor review and approval before any action is taken.

---

## UI Screenshots

| Step 1 — Patient | Step 2 — Consultation Notes | Step 3 — Prescription |
|---|---|---|
| ![Patient selection screen](docs/screenshots/step1_patient.png) | ![Consultation notes screen](docs/screenshots/step2_notes.png) | ![Prescription upload screen](docs/screenshots/step3_prescription.png) |

The interface walks the doctor through a 3-step flow: select/register the patient → record or type consultation notes → upload the prescription image. Each step feeds the next, and the AI processes inputs in the background before presenting results for doctor review.

Once past the patient entry screen, a **hamburger menu** appears in the top-right corner of the header, giving the doctor quick access to patient-specific features — Patient Insights, Visit History, Reports, Prescriptions, Vitals tracker, and Allergies & alerts — without disrupting the consultation flow.

---

## Why This Exists

In a small general clinic seeing 10–15 patients a day:

- Prescriptions are handwritten and unstructured
- Blood reports require manual scanning for abnormalities
- Patient history is fragmented or memory-dependent
- Doctors spend time on repetitive cognitive work instead of patient care

This system **augments the doctor, not replaces them.**

---

## What's Been Built

### Phase 1 — Prescription Reader
Upload a handwritten or printed prescription (image). The agent extracts structured medication details:

| Field | Example |
|---|---|
| Medicine name | Amoxicillin |
| Dosage | 500 mg |
| Frequency | `1-0-1` → Morning and Night |
| Meal timing | `AC` → Before food |
| Duration | 5 days |
| Special instructions | Avoid alcohol |

*See [Step 3 — Prescription upload](#ui-screenshots) above.*

---

### Phase 2 — Consultation Notes Agent
Record a doctor's spoken consultation (in Telugu, Hindi, or English mix). The agent transcribes and structures it into:

- Chief complaints
- History
- Examination findings
- Diagnosis impression *(only if doctor states it — never inferred)*
- Instructions
- Follow-up

**Supports:** Telugu + Hindi + English code-switching  
**Input:** `.m4a`, `.mp3`, `.wav`, `.webm` audio files

*See [Step 2 — Consultation Notes](#ui-screenshots) above.*

---

### Phase 3 — WhatsApp Message Generator
Takes the structured prescription (and optional consultation notes) and generates a patient-friendly WhatsApp message:

```
Hi [Patient Name],

Here are your medicines from today's visit:

💊 Amoxicillin 500mg — After breakfast and after dinner — for 5 days
💊 Paracetamol 650mg — After food (only if fever) — as needed

Rest well and drink plenty of fluids.

If you have any concerns, please call the clinic.
⚠️ Please confirm with your doctor before any changes.
```

*See [UI Screenshots](#ui-screenshots) above.*

---

### Phase 4 — Blood Report Analyser *(Latest)*
Upload a blood report PDF. The system runs two agents in sequence:

**Agent 1 — Report Reader**
Extracts every parameter with value, unit, reference range, and status:

| Parameter | Value | Unit | Range | Status |
|---|---|---|---|---|
| Haemoglobin | 9.2 | g/dL | 13.0–17.0 | 🔴 Low |
| Blood Glucose (F) | 92 | mg/dL | 70–100 | 🟢 Normal |
| Platelets | 48,000 | cells/μL | 1.5L–4.5L | 🔴 Critical |

**Agent 2 — Summary Generator**
Produces a plain-English summary the doctor can review:

> *"Most of your blood test results are within the normal range. Your haemoglobin is slightly low and your platelet count needs immediate attention — your doctor will discuss this with you."*

*See [UI Screenshots](#ui-screenshots) above.*

---

### Phase 5 — Patient Insights + Hamburger Menu *(Latest)*
After every doctor-approved save (prescription, consultation, or blood report), the system automatically regenerates insights from the full patient history and caches them in Firestore.

**What it analyses:**
- Blood parameter trends across reports (e.g. Hb declining visit-over-visit)
- Recurring complaints and diagnoses across consultations
- Medications that keep reappearing (suggesting chronic or unresolved conditions)

**What it produces (`PatientInsights`):**

| Field | Description |
|---|---|
| `trends` | Per-parameter trend with direction: improving / worsening / stable / fluctuating |
| `risk_flags` | Predicted risks with severity (low/medium/high) and supporting evidence |
| `recurring_patterns` | Complaints, medications, or diagnoses appearing across multiple visits |
| `overall_assessment` | Plain-English paragraph for the doctor summarising the health trajectory |

**Example risk flag:**
> *"Haemoglobin has dropped from 13.2 → 11.8 → 10.2 g/dL across 3 reports despite iron prescription — possible compliance issue or absorption problem."*

Insights are cached under `patients/{phone}/insights/latest` and refreshed on every save. The doctor can also trigger a manual refresh.

**Hamburger menu UI:**
The insights are surfaced via a slide-out drawer accessible from any screen after patient entry. Tapping **Patient Insights** opens a full-screen panel that loads the cached insights and renders them as structured cards. The drawer also acts as an extensibility hub for upcoming features:

| Section | Status |
|---|---|
| Patient Insights | ✅ Live |
| Visit History | Coming soon |
| Reports (Blood reports, X-rays, MRIs) | Coming soon |
| Prescriptions | Coming soon |
| Vitals tracker | Coming soon |
| Allergies & alerts | Coming soon |

---

### Patient History Store
All doctor-approved records are saved to **Cloud Firestore** — a distributed, serverless document database.

**Structure:**
```
patients/
  {phone_number}/
    profile        → name, age, gender
    prescriptions/ → timestamped prescription records
    consultations/ → timestamped consultation notes
    blood_reports/ → timestamped report + summary pairs
```

- Phone number is the patient identifier (aligns with WhatsApp)
- Saving only happens **after doctor approves** the output
- Globally distributed, scales automatically, free tier for clinic workloads

---

## Architecture

```
                        ┌─────────────────────┐
                        │   Doctor Interface   │
                        │  (FastAPI + Web UI)  │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │       Root Orchestrator      │
                    │       (clinical_copilot)     │
                    └──┬──────┬──────┬──────┬─────┘
                       │      │      │      │
           ┌───────────▼┐ ┌───▼──┐ ┌▼────┐ ┌▼──────────────┐
           │Prescription│ │Notes │ │Msg  │ │  Blood Report  │
           │  Reader    │ │Agent │ │Agent│ │ Reader+Summary │
           └───────────┬┘ └───┬──┘ └┬────┘ └┬──────────────┘
                       │      │      │       │
                    ┌──▼──────▼──────▼───────▼──┐
                    │      Doctor Review         │
                    │   (approve / edit / skip)  │
                    └──────────────┬─────────────┘
                                   │ approved
                    ┌──────────────▼─────────────┐
                    │     Cloud Firestore         │
                    │   Patient History Store     │
                    └────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | Google ADK (`google-adk`) |
| AI model | Gemini 2.0 Flash (Vertex AI / AI Studio) |
| API server | FastAPI + Uvicorn |
| Patient store | Cloud Firestore (distributed, serverless) |
| Audio | Google GenAI Files API |
| Language | Python 3.11+ |
| Package manager | `uv` |

---

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/prescription/read` | Upload prescription image → structured JSON |
| POST | `/api/notes/process` | Upload audio or text → consultation notes JSON |
| POST | `/api/message/generate` | Generate WhatsApp message from prescription |
| POST | `/api/bloodreport/analyze` | Upload blood report PDF → extract + summarise |
| POST | `/api/patient/save/prescription` | Doctor-approved save to patient history |
| POST | `/api/patient/save/consultation` | Doctor-approved save to patient history |
| POST | `/api/patient/save/bloodreport` | Doctor-approved save to patient history |
| GET | `/api/patient/{phone}/history` | Full patient history |
| GET | `/api/patient/{phone}/profile` | Patient profile |
| GET | `/api/patient/{phone}/insights` | Cached insights (202 if not yet generated) |
| POST | `/api/patient/{phone}/insights/refresh` | Force regenerate insights and return result |

---

## Running Locally

```bash
# Clone
git clone https://github.com/ravikiran-tummala/clinical_agent.git
cd clinical_agent/clinical-agent

# Install dependencies
uv sync

# Set AI Studio API key (personal Gmail — free tier)
export GOOGLE_API_KEY="your-key-from-aistudio.google.com"

# Run the UI
uv run python ui_app.py
# Open http://localhost:8080
```

---

## Safety & Compliance

| Rule | Detail |
|---|---|
| No autonomous diagnosis | Agents never infer diagnosis unless doctor explicitly states it |
| No treatment suggestions | Agents only structure what the doctor has already prescribed |
| Doctor approval gate | Nothing is saved or sent to a patient without explicit approval |
| Disclaimers on all outputs | Every AI output carries `"AI extraction — doctor must verify before use"` |
| Audit trail | All saves timestamped in Firestore |

---

## Roadmap

- [x] Phase 1 — Prescription reader + structured JSON
- [x] Phase 2 — Consultation notes from audio (Telugu/Hindi/English)
- [x] Phase 3 — WhatsApp message generator
- [x] Phase 4 — Blood report analyser + plain-English summary
- [x] Patient history store (Firestore, phone-keyed)
- [x] Phase 5 — Patient insights: trends, risk flags, recurring patterns (auto-cached on every save)
- [x] Hamburger menu UI with slide-out drawer and live Patient Insights panel
- [ ] Visit history UI
- [ ] Reports UI (blood reports, X-rays, MRIs)
- [ ] Prescriptions history UI
- [ ] Vitals tracker with trend charts
- [ ] Allergies & alerts management
- [ ] Radiology report support
- [ ] WhatsApp Business API integration
- [ ] Follow-up reminders

---

## Disclaimer

This software is intended strictly as a **clinical decision support tool**.

- It does **not** provide diagnoses
- It does **not** recommend treatments
- It does **not** replace medical judgment

Final medical decisions must always be made by a licensed physician.
