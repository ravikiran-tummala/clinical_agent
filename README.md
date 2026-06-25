# 🩺 Clinical Co-Pilot — Agentic AI Assistant for Small Clinics

An AI-powered clinical assistant built for small general clinics in India. It reduces the doctor's cognitive load by structuring handwritten prescriptions, transcribing consultation audio, analysing blood reports, and maintaining a persistent patient history — while keeping the doctor fully in control of every decision.

> **This is a clinical decision support tool, not a medical device.**
> All outputs require doctor review and approval before any action is taken.

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

> Screenshot coming soon

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

> Screenshot coming soon

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

> Screenshot coming soon

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

> Screenshot coming soon

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
- [ ] UI for patient timeline view
- [ ] Trend detection across visits (e.g. rising glucose)
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
