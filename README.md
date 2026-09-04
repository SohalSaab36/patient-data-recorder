# SIH26047 – MediKiosk (Smart Patient Case-Taking Platform)

MediKiosk is a local Flask application for **SIH26047**. It helps a patient record a structured clinical history on a kiosk-style portal, upload previous documents, and produce a **physician-ready summary** that a doctor can edit and confirm.

It is a **clinical history-taking and documentation assistance** prototype. It does **not** diagnose disease, replace a doctor, recommend treatment, or act as a certified medical device.

The earlier MediCase doctor workflow is still present: staff login, patient register/search/edit, classic multi-step case sheets, print, and PDF export.

## SIH26047 alignment

Inspired by platforms such as MediKiosk-style AI clinical history software, this build covers:

1. Patient identify / register / login  
2. Preferred language (English / Hindi)  
3. Consent before history and document processing  
4. Guided conversational interview (text, large buttons, optional voice)  
5. Document upload and digitization  
6. Rule-based extraction from OCR text  
7. Chronological medical timeline  
8. Structured physician summary  
9. Doctor review, edit, confirm, or send back  
10. Accessibility mode for elderly and low-literacy users  

## Features

**Patient portal**

- Registration and login  
- Consent centre (history, documents, clinician sharing, ABDM demo)  
- Adaptive interview (JSON flows in `data/interview_flows.json`)  
- Optional AYUSH / Ayurvedic assessment (stored separately)  
- Document upload (PDF/JPG/PNG) with OCR status  
- Timeline and previous summaries  
- ABHA **sandbox** (no real ABDM APIs)

**Doctor / admin**

- Dashboard: totals, pending interviews, priority phrase alerts, uploads  
- Patient workspace: details, timeline, documents, summary, labs, alerts  
- Classic case-taking form (preserved)  
- Summary draft / confirm / reject, print, PDF  
- Admin: users, stats, audit log  

**Safety layers**

- Configurable red-flag **phrases** (`data/red_flags.json`) — priority marking, not diagnosis  
- Lab flags: within range / potentially low / high / needs review — for clinician review only  
- Rule-based summaries by default; optional HTTP AI if `AI_API_KEY` is set  

## Architecture

```
Browser (kiosk + clinician UI)
    → Flask routes (auth, portal, patients, cases, documents, clinical, admin)
        → SQLAlchemy / MySQL
        → services/
            interview_engine.py   rule-based question flow
            ai_service.py         rule-based summary + optional API
            ocr_service.py        Tesseract/pdf2image with fallback
            extraction_service.py regex extraction
            abdm_service.py       sandbox ABHA / FHIR-like bundle
```

New interview tables sit **beside** existing `users`, `patients`, `medical_cases`, and `medical_histories`. On startup, `database/migrate.py` creates new tables and adds missing patient/user columns without dropping data.

## Tech stack

- HTML, CSS, JavaScript, Bootstrap 5  
- Python, Flask, Flask-Login, Flask-SQLAlchemy  
- MySQL via PyMySQL  
- ReportLab PDFs  
- Optional: Pillow, pytesseract, pdf2image  

## Folder structure

```text
app.py, config.py, extensions.py, requirements.txt
models/          users, patients, cases, interview, documents, consents
routes/          auth, dashboard, patients, cases, portal, documents, clinical, admin
services/        interview, AI, OCR, extraction, ABDM, consent, pipeline
data/            interview_flows.json, red_flags.json
templates/       staff UI, portal kiosk, clinical summary
static/          css, js, images
database/        schema.sql, setup_db.py, migrate.py
uploads/documents   created at runtime
```

## Installation

```powershell
cd "path\patient rec"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with your MySQL password and a strong `SECRET_KEY`.

Create the database:

```powershell
python database/setup_db.py
```

Or: `CREATE DATABASE patient_case_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`

## Environment variables

| Variable | Purpose |
| --- | --- |
| `MYSQL_*` | Database connection |
| `SECRET_KEY` | Session signing |
| `TESSERACT_CMD` | Full path to `tesseract.exe` if not on PATH |
| `POPPLER_PATH` | Poppler `bin` folder for PDF OCR |
| `AI_PROVIDER` | `none` (default) or a provider name |
| `AI_API_KEY` / `AI_API_URL` / `AI_MODEL` | Optional chat-completions style summarization |

Do not put API keys in source files.

## OCR setup (optional)

1. Install [Tesseract OCR](https://github.com/tesseract-ocr/tesseract).  
2. For PDFs, install Poppler and set `POPPLER_PATH`.  
3. If these are missing, uploads still succeed with status **Needs manual review**.

## Run

```powershell
python app.py
```

Open http://127.0.0.1:5000

### Demo credentials

| Role | Username | Password |
| --- | --- | --- |
| Patient | `patient` | `patient123` |
| Doctor | `doctor` | `doctor123` |
| Admin | `admin` | `admin123` |

Change these before any real deployment.

### Typical demo path

1. Sign in as **patient** → Consent → grant history, documents, sharing.  
2. Start health interview; try a chest-pain path or type a red-flag phrase.  
3. Upload a sample report.  
4. Sign in as **doctor** → open the patient → review summary → confirm or send back.

## Limitations of this prototype

- Question flows are rule-based, not a full LLM clinician.  
- OCR and extraction are **not** medical-grade.  
- Red flags are phrase matches only.  
- ABHA/ABDM screens are a **sandbox**.  
- Not DPDP-certified; consent UI is educational.  
- Not for unsupervised emergency care.

## AI disclaimer

Summaries are assembled from answers and extracted text. If no AI key is configured, generation is deterministic/rule-based. Optional APIs must not be treated as a diagnostic engine.

## ABDM demo disclaimer

`services/abdm_service.py` only simulates verify/link/FHIR-like JSON. **No national health ID or ABDM production API is called.**

## Classic doctor case sheet

Staff can still open a patient and use **Classic case sheet** (previous multi-step form + PDF). Kiosk interviews add a parallel structured summary.
