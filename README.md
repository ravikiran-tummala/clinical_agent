🩺 Agentic Doctor Co-Pilot for Small Clinics

An agentic AI-powered clinical assistant designed for small general clinics to reduce cognitive load, structure unorganized data, and improve continuity of care — while keeping the doctor fully in control.

🎯 Motivation

In small general clinics (10–15 patients/day):

Prescriptions are often handwritten and unstructured Diagnostic reports require manual scanning for abnormalities Past patient history is fragmented or memory-dependent Doctors spend time on repetitive cognitive work instead of patient care

👉 This system focuses on augmenting the doctor, not replacing them.

🧠 Core Design Principles Doctor-first (no autonomous decisions) Human-in-the-loop for all critical actions Agentic architecture (modular, auditable agents) Safety > Intelligence Practical for small clinics, not enterprise-heavy 🧩 System Overview

The system is composed of specialized, independent agents:

1️⃣ Intake Agent Inputs: Handwritten prescriptions (images) Lab / radiology reports (PDFs) Typed notes Patient-uploaded documents Responsibilities: OCR extraction Input validation Data normalization Metadata tagging (date, type, patient) 2️⃣ Prescription Intelligence Agent Converts: Handwritten / typed prescriptions → structured format Outputs: Medicine name Dosage Frequency Duration Special instructions Detects: Ambiguities (e.g., unclear abbreviations) Missing dosage/timing Enhancements: Generates structured clinical notes Suggests clarification prompts (for doctor review) 🧾 Medication Communication Layer (NEW)

Generates patient-friendly medication instructions:

“Take after food” “Morning / afternoon / night” “For 5 days” Conditional instructions (e.g., fever-based meds)

Supports:

Multi-language (English, Hindi, Telugu) WhatsApp-ready formatting

⚠️ Always requires doctor approval before sharing

3️⃣ Diagnostics Triage Agent Supports: Blood reports Radiology reports (X-ray, MRI, CT summaries) Capabilities: Extracts values & reference ranges Flags abnormalities: 🔴 High attention 🟠 Borderline 🟢 Normal Outputs: Doctor-facing technical summary Optional patient-friendly explanation (disabled by default) Safety: ❌ No diagnosis ❌ No treatment suggestions ✅ “May indicate…” style phrasing only 4️⃣ Longitudinal Memory Agent Maintains: Patient visit history Prescriptions Diagnostic summaries Uploaded images/reports Capabilities: Timeline view across visits Trend detection: Rising glucose Falling hemoglobin Persistent abnormalities Example Output:

“Repeated borderline fasting glucose observed across last 3 visits.”

Design Constraint: ❌ No predictions ✅ Only retrospective insights 5️⃣ Follow-up & Recall Agent (NEW) Purpose:

Ensures continuity of care

Features: Doctor-defined follow-ups: “Visit after 5 days” “Repeat blood test after 3 months” Automated reminders: WhatsApp (preferred) SMS (optional) Benefits: Improves patient adherence Increases revisit consistency 6️⃣ Patient Timeline Interface (NEW)

A unified clinical memory system per patient:

Displays: Visit history Prescriptions Reports Images Doctor notes Capabilities: Chronological navigation Before/after comparison (e.g., skin images) Quick summary per visit 7️⃣ Voice-to-Notes Agent (NEW) Problem:

Doctors don’t want to type.

Solution: Convert spoken notes → structured clinical notes Example:

Input:

“Patient has fever for 2 days with mild cough…”

Output:

Structured SOAP-style notes 8️⃣ Safety & Governance Agent

A mandatory guardrail layer ensuring system safety.

Responsibilities: Blocks: Diagnosis generation Treatment recommendations Enforces: Doctor approval workflows Adds: Medico-legal disclaimers Maintains: Full audit logs of AI outputs and actions 🔐 Safety & Compliance

This system is designed with strict safety constraints:

🚫 Prohibited: Diagnosis Treatment recommendations Autonomous patient communication ✅ Enforced: Doctor approval before: Saving data Sending patient messages Explicit disclaimers on all outputs Full audit logging Transparent AI behavior

This is a clinical assistant, not a medical device.

📦 MVP Scope (Phase 1)

Focus on high-value, low-risk features:

Core: Prescription → structured summary Blood report → abnormality highlighting Doctor review & approval interface Added High-Impact Features: Medication instruction generator Patient timeline (basic) Follow-up reminders (manual trigger) Target Build Time:

2–3 weeks

🚀 Roadmap Phase 1 (MVP) Prescription structuring Blood report triage Doctor approval workflow Patient timeline (read-only) Medication messaging Phase 2 Radiology report support Trend detection across visits Voice-to-notes WhatsApp integration Phase 3 Patient communication (with consent) Automated follow-up reminders Clinic analytics dashboard 🛠️ Suggested Tech Stack Backend: Python (FastAPI) AI Layer: LLM (GPT-4 / GPT-4.1 / equivalent) OCR: Tesseract / Google Vision / AWS Textract Storage: Relational DB (PostgreSQL) → structured data Object storage (S3/GCS) → reports & images Vector DB → semantic retrieval (optional) Frontend: Web dashboard (doctor-facing) Optional: iOS app (doctor) Lightweight patient interface Integrations: WhatsApp Business API (critical for India) SMS fallback 📊 Success Metrics ⏱️ Time saved per patient 🧾 Reduction in manual prescription rewriting 🧪 Accuracy of abnormality detection 🔁 Daily active usage by doctor ✍️ Doctor edits per AI-generated summary 📲 Patient adherence to medication & follow-ups 🚧 Non-Goals

This project explicitly does NOT aim to:

Replace doctors Provide diagnoses Automate treatment decisions Operate without doctor oversight Act as a standalone medical system 🧪 Example Workflow Doctor uploads prescription AI structures medication + instructions Doctor reviews & edits Patient receives clean instructions (WhatsApp) Patient uploads blood report AI highlights abnormal values Doctor reviews summary Stored in patient timeline 🤝 Contributing

We welcome:

Clinicians (validation & feedback) Engineers (architecture, reliability) Researchers (agentic systems in healthcare) Contribution Rule:

All contributions must strictly preserve safety constraints.

⚠️ Disclaimer

This software is intended strictly as a clinical decision support tool.

It does NOT provide diagnoses It does NOT recommend treatments It does NOT replace medical judgment

Final medical decisions must always be made by a licensed physician.
