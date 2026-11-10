# MazdoorMitra

A voice-first wage and work-record platform for India's daily-wage, construction, domestic, and migrant workers. Workers speak naturally in Hindi or Hinglish to log work, record payments, and generate verifiable wage statements — no literacy or manual data entry required.

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Voice Pipeline](#voice-pipeline)
- [Local Evon v3.3 Transformers Runtime](#local-evon-v33-transformers-runtime)
- [Wage Calculation Engine](#wage-calculation-engine)
- [PDF Statement Generation](#pdf-statement-generation)
- [Testing](#testing)
- [License](#license)

## Architecture

```
                       ┌──────────────────┐
                       │   Next.js 16     │
                       │   React 19       │
                       │   Tailwind CSS   │
                       │   Port 3000      │
                       └────────┬─────────┘
                                │ REST / JSON
                       ┌────────▼─────────┐
                       │   FastAPI 0.115  │
                       │   Pydantic v2    │
                       │   SQLAlchemy 2.0 │
                       │   Port 8000      │
                       └──┬─────┬─────┬───┘
                          │     │     │
               ┌──────────▼┐ ┌─▼───┐ ┌▼──────────┐
               │  Gnani    │ │ DB  │ │  Gnani    │
               │  Prisma   │ │     │ │  Evon     │
               │  (STT)    │ │     │ │  (LLM)    │
               └───────────┘ └─────┘ └───────────┘
                                │
                          ┌─────▼─────┐
                          │  Gnani    │
                          │  Timbre   │
                          │  (TTS)    │
                          └───────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript 5, Tailwind CSS 4 |
| Backend | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) |
| Database | SQLite (development) / PostgreSQL via asyncpg (production) |
| Speech-to-Text | Gnani Prisma |
| NLP Extraction | Gnani Evon |
| Text-to-Speech | Gnani Timbre |
| Auth | JWT (HS256) with PIN-based login |
| PDF Generation | ReportLab |

## Project Structure

```
mazdoormitra/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py              # Registration and PIN login
│   │   │   ├── voice.py             # Voice session lifecycle
│   │   │   ├── ledger.py            # Work entries, payments, summaries
│   │   │   ├── employers.py         # Employer CRUD
│   │   │   ├── payments.py          # Payment routes (gateway placeholder)
│   │   │   └── statements.py        # Statement history and PDF download
│   │   ├── database/
│   │   │   ├── connection.py        # Async engine, session factory, migrations
│   │   │   └── migrations.sql       # Reference DDL
│   │   ├── models/
│   │   │   └── models.py            # SQLAlchemy ORM models
│   │   ├── schemas/
│   │   │   ├── auth.py              # Auth request/response schemas
│   │   │   ├── employer.py          # Employer schemas
│   │   │   ├── ledger.py            # Ledger, work entry, payment schemas
│   │   │   ├── statement.py         # Statement schemas
│   │   │   └── voice.py             # Voice session schemas
│   │   ├── services/
│   │   │   ├── wage_calculator.py   # Deterministic Decimal arithmetic
│   │   │   ├── extraction_service.py # AI output validation and sanitization
│   │   │   ├── conversation_service.py # Multi-turn voice state machine
│   │   │   ├── pdf_service.py       # Bilingual PDF generation
│   │   │   ├── prisma_service.py    # Gnani STT client
│   │   │   ├── evon_service.py      # Gnani LLM client
│   │   │   ├── timbre_service.py    # Gnani TTS client
│   │   │   └── ledger_service.py    # Ledger business logic
│   │   ├── utils/
│   │   │   ├── auth.py              # JWT creation and verification
│   │   │   └── validators.py        # Input validators
│   │   ├── tests/                   # pytest suite (workflow, migration, and arithmetic coverage)
│   │   ├── config.py                # pydantic-settings configuration
│   │   └── main.py                  # Application entry point
│   ├── requirements.txt
│   ├── smoke_gnani.py               # Live provider smoke test
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Landing / home
│   │   ├── layout.tsx               # Root layout (AuthProvider, Navbar)
│   │   ├── auth/page.tsx            # Registration and login
│   │   ├── dashboard/page.tsx       # Financial dashboard
│   │   ├── voice/page.tsx           # Voice recording and confirmation
│   │   ├── voice-studio/page.tsx    # Gnani Timbre Voice Studio
│   │   ├── employers/page.tsx       # Employer management
│   │   ├── history/page.tsx         # Transaction timeline
│   │   └── statements/page.tsx      # Statement history and PDF download
│   ├── components/
│   │   ├── Navbar.tsx
│   │   ├── VoiceRecorder.tsx
│   │   ├── WageSummary.tsx
│   │   ├── PaymentHistory.tsx
│   │   ├── WorkHistory.tsx
│   │   ├── EmployerCard.tsx
│   │   ├── ConfirmationCard.tsx
│   │   ├── TranscriptCard.tsx
│   │   └── LanguageSelector.tsx
│   ├── lib/
│   │   ├── api.ts                   # API client with JWT injection
│   │   └── auth-context.tsx         # Auth state provider
│   ├── types/
│   │   └── index.ts                 # Shared TypeScript interfaces
│   ├── package.json
│   ├── tsconfig.json
│   └── pnpm-lock.yaml
├── pytest.ini
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11 or later
- Node.js 20 or later
- pnpm 10 or later

### Backend

```bash
cd backend
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env — at minimum set JWT_SECRET_KEY

uvicorn app.main:app --reload --port 8000
```

The server starts at `http://localhost:8000`. Interactive API docs are available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

The app starts at `http://localhost:3000`.

### Generate a JWT Secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Environment Variables

All backend configuration is managed through `backend/.env`. See `backend/.env.example` for the full template.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./test.db` | Database connection string. Use `postgresql+asyncpg://...` for production. |
| `JWT_SECRET_KEY` | Yes | — | 256-bit secret for signing JWT tokens. |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm. |
| `JWT_EXPIRATION_MINUTES` | No | `1440` | Token expiry (default 24 hours). |
| `GNANI_PRISMA_API_KEY` | For voice | — | Gnani Prisma (STT) API key. |
| `GNANI_PRISMA_API_URL` | For voice | `https://api.vachana.ai/stt/v3` | Prisma endpoint. |
| `GNANI_EVON_API_KEY` | For voice | — | Gnani Evon API key with the required beta/service scope. |
| `GNANI_EVON_API_URL` | For voice | `https://api.vachana.ai/v1/chat/completions` | Evon endpoint. |
| `GNANI_EVON_BACKEND` | No | `api` | `api` for the configured service or `transformers` for a compatible Linux/CUDA host. |
| `GNANI_EVON_MODEL_ID` | No | `gnani/gnani-evon-v3.3-30B-A3B` | Local model ID when the Transformers backend is selected. |
| `GNANI_TIMBRE_API_KEY` | For voice | — | Gnani Timbre (TTS) API key. |
| `GNANI_TIMBRE_API_URL` | For voice | `https://api.vachana.ai/api/v1/tts/inference` | Timbre endpoint. |
| `CORS_ORIGINS` | No | `["http://localhost:3000"]` | Allowed CORS origins (JSON array or comma-separated). |

The application runs without Gnani API keys — voice features return provider errors, but other functionality (auth, ledger, employers, statements) remains available. An Evon API 403 is treated as an upstream failure; the app preserves the transcript and never substitutes fake extraction output.

## API Reference

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Returns service status, name, and version. |

### Authentication (`/api/auth`)

PIN-based authentication designed for workers without email addresses.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register with name, phone, PIN, and preferred language. Returns JWT. |
| `POST` | `/api/auth/login` | Login with phone and PIN. Returns JWT. |

### Voice Sessions (`/api/voice`)

Full voice session lifecycle — from audio upload through extraction, clarification, and confirmation.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/voice/sessions` | Create a new voice session. |
| `POST` | `/api/voice/sessions/{id}/audio` | Upload WAV audio (max 12 MB) for transcription. |
| `POST` | `/api/voice/sessions/{id}/extract` | Run NLP extraction on transcript. Returns structured data or follow-up question. |
| `POST` | `/api/voice/sessions/{id}/reply` | Submit text reply to a clarification question. |
| `POST` | `/api/voice/sessions/{id}/reply/audio` | Submit spoken reply to a clarification question. |
| `POST` | `/api/voice/sessions/{id}/correct` | Apply manual corrections to extracted fields. |
| `POST` | `/api/voice/sessions/{id}/confirm` | Confirm and persist extraction as a ledger record. |
| `POST` | `/api/voice/sessions/{id}/reject` | Discard the session without persisting. |
| `POST` | `/api/voice/sessions/{id}/speak` | Generate TTS audio receipt of the confirmed record. |
| `GET` | `/api/voice/capabilities` | Provider-specific speech languages, models, voices, and access status. |
| `POST` | `/api/voice/studio/generate` | Generate audio using a published Timbre model/voice combination. |
| `GET` | `/api/voice/studio/history` | List the worker's TTS generation history. |
| `DELETE` | `/api/voice/studio/history/{id}` | Delete one worker-owned TTS history item. |

### Ledger (`/api/ledger`)

All endpoints enforce per-worker data isolation.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/ledger/summary` | Aggregated financial summary with optional employer/date filters. |
| `GET` | `/api/ledger/work` | List work entries with pagination and filters. |
| `POST` | `/api/ledger/work` | Manually create a work entry. |
| `GET` | `/api/ledger/payments` | List payments with pagination and filters. |
| `POST` | `/api/ledger/payments` | Manually record a payment. |
| `GET` | `/api/ledger/transactions` | Unified reverse-chronological timeline of work and payment records. |

### Employers (`/api/employers`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/employers` | List all employers for the authenticated worker. |
| `POST` | `/api/employers` | Add a new employer (unique per worker). |
| `GET` | `/api/employers/{id}/worksites` | List this worker's worksites for an employer. |
| `POST` | `/api/employers/{id}/worksites` | Add a named, worker-owned worksite. |
| `GET` | `/api/employers/{id}/agreements` | List reported, effective-dated wage agreements. |
| `POST` | `/api/employers/{id}/agreements` | Add a daily/hourly wage agreement with optional site and dates. |

### Kaam Diary (`/api/ledger`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/ledger/calendar?year=&month=` | Summarize dates with persisted work records. Empty dates do not imply absence. |
| `PUT` | `/api/ledger/work/{id}` | Correct a work entry, recalculate wages, and append before/after audit details. |

Corrections are rejected when the new wage would fall below amounts already allocated to the work or when it conflicts with an allocated employer payment.

### Statements (`/api/statements`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/statements` | Paginated list of voice statements. |
| `GET` | `/api/statements/{id}` | Full statement detail including extracted data and conversation history. |
| `GET` | `/api/statements/{id}/pdf` | Download a bilingual PDF wage statement (confirmed statements only). |
| `GET` | `/api/statements/export?start_date=&end_date=&employer_id=` | Download a bilingual PDF for a worker-scoped period/employer slice, with each record labelled reported or worker-confirmed. |

### Evidence Vault (`/api/evidence`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/evidence` | Consent-gated private upload (PDF, JPEG, PNG, WebP, WAV, WebM; 12 MB limit). |
| `GET` | `/api/evidence` | List worker-owned metadata only. |
| `GET` | `/api/evidence/{id}/preview` | Authenticated inline preview for supported content types. |
| `GET` | `/api/evidence/{id}/download` | Authenticated attachment download. |
| `DELETE` | `/api/evidence/{id}` | Delete worker-owned file and metadata. |

Uploads are signature-checked, stored under the ignored `backend/.private-evidence/` directory, and associated with at most one worker-owned record. This is private local storage for the current deployment; production should use a private object-storage bucket and managed backups.

### Financial Insights and Assistance

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/insights?months=6` | Deterministic monthly and employer summaries computed from ledger rows. |
| `GET/POST` | `/api/insights/savings-goals` | List or create worker-entered savings targets; targets do not track actual savings. |
| `PATCH/DELETE` | `/api/insights/savings-goals/{id}` | Pause/reopen or delete a worker-owned goal. |
| `GET` | `/api/assistance/resources` | Official e-Shram and SAMADHAN resource links. |
| `GET` | `/api/assistance/faqs` | General record-keeping guidance. |
| `GET` | `/api/assistance/payment-request` | Prepare a neutral, copy-only message from the recorded positive balance. No message is sent. |

## Database Schema

Sixteen worker-scoped tables with UUID primary keys (`String(36)` for SQLite/PostgreSQL portability). All monetary columns use `Numeric(15, 2)` to prevent floating-point errors.

```
workers
├── employers             (worker_id FK)
├── work_entries          (worker/employer/source-statement FKs)
├── payments              (worker/employer/source-statement FKs)
├── payment_allocations   (worker/payment/work FKs; partial amount allocations)
├── voice_statements      (worker_id FK)
├── evidence_files        (worker/statement FKs)
├── audit_events          (worker FK; append-only change history)
├── worksites             (worker/employer FKs)
├── wage_agreements       (worker/employer/worksite FKs)
├── wage_calculations     (immutable work-entry breakdown snapshots)
├── worker_preferences    (worker-owned privacy/accessibility preferences)
├── voice_generation_history (worker-owned Timbre history)
├── reminder_preferences  (explicit consent and cadence)
├── reminders             (worker-owned in-app reminders)
└── savings_goals         (worker-entered goals)
```

**Statement status lifecycle:**
`INITIAL` → `TRANSCRIBED` → `EXTRACTED` → `AWAITING_INFORMATION` ↔ (clarification loop) → `READY_FOR_CONFIRMATION` → `CONFIRMED` | `REJECTED`

**Payment types:** `cash`, `upi`, `bank`, `advance`, `other`

## Voice Pipeline

The voice pipeline is a stateful, multi-turn conversation that converts spoken Hindi, English, or Hinglish into structured ledger records. Prisma and Timbre capability metadata lists the ten documented Indian/English languages separately; complete multilingual Evon extraction depends on the selected backend and runtime/account access:

1. **Record** — Worker speaks naturally ("Sharma ji ke yahan 3 din kaam kiya, 500 rupay daily").
2. **Transcribe** — Gnani Prisma converts speech to text.
3. **Extract** — Gnani Evon parses intent (`log_work` or `log_payment`), employer name, amounts, dates, and duration from the transcript.
4. **Validate** — `ExtractionService` sanitizes AI output: enforces numeric bounds, caps field lengths, validates payment types, and identifies missing required fields.
5. **Clarify** — If fields are missing, the system generates a localized follow-up question (Hindi or English). The worker can reply by voice or text. This loop repeats until all required fields are present.
6. **Confirm** — Worker reviews the extracted summary and confirms or rejects.
7. **Persist** — On confirmation, the system atomically creates the corresponding `WorkEntry` or `Payment` record, resolves or creates the `Employer`, and marks the statement as `CONFIRMED`.
8. **Receipt** — Gnani Timbre generates a spoken audio receipt of the confirmed record. A provider failure leaves the saved record intact.

## Local Evon v3.3 Transformers Runtime

The Evon adapter can use Gnani's `gnani/gnani-evon-v3.3-30B-A3B` through Transformers. It loads lazily on the first extraction and uses `trust_remote_code=True` as shown by the [official model card](https://huggingface.co/gnani/gnani-evon-v3.3-30B-A3B).

Use this only on a provisioned Linux NVIDIA CUDA inference host. The published checkpoint is BF16 with 30B total parameters; the model card lists H100 80 GB/H200/A100-class hardware and Transformers 5.3+. A 4 GB laptop GPU is not sufficient.

```bash
cd backend
pip install -r requirements-evon-local.txt
# Set in backend/.env:
# GNANI_EVON_BACKEND=transformers
# GNANI_EVON_MODEL_ID=gnani/gnani-evon-v3.3-30B-A3B
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The current Windows/RTX 2050 (4 GB) workstation cannot run this model. The optional adapter is implemented but local inference has not been verified here. See the [model card runtime and hardware notes](https://huggingface.co/gnani/gnani-evon-v3.3-30B-A3B).

## Wage Calculation Engine

All financial arithmetic uses Python `Decimal` with `ROUND_HALF_UP` quantization to two decimal places. Floating-point types are not accepted.

- **Work entry total:** daily or explicit hourly rate, plus separately itemized overtime using the recorded multiplier. All values are recomputed with `Decimal` on the backend and shown before the worker confirms.
- **Balance:** `total_earned - total_received` (positive = owed to worker, negative = overpaid)
- **Payment allocation:** A payment can be applied partially to one or more work entries. Allocation links are capped by both the remaining payment and work amounts; they never count the payment twice.
- **Summary:** Computes `total_earned`, `total_received`, `total_advances`, `balance`, `pending`, `overpaid`, `total_work_days` — both overall and per-employer. Changing rates on later work entries preserves the earlier agreed amount.

## PDF Statement Generation

Generates A4 wage statements using ReportLab with:

- Bilingual headers (English and Hindi)
- Worker and employer details
- Confirmation status and timestamp
- Original voice transcript
- Financial summary table
- Itemized work entries and payments
- Indian number formatting (e.g., 1,23,456.78)
- Legal disclaimer clarifying worker self-reporting

## Testing

### Backend

```bash
cd backend
python -m pytest -v app/tests
```

The test suite covers:
- Wage calculation (deterministic Decimal arithmetic, edge cases)
- Extraction validation (bounds checking, sanitization, missing field detection)
- Conversation state machine (state transitions, follow-up generation, reply parsing)
- PDF generation (layout, formatting, content)
- Voice API workflow (confirmation gate, duplicate detection, provider failures, hourly overtime, spoken receipts)
- Database migration preservation, audit ownership, partial allocations, worksite/agreement scoping, audited corrections, private evidence uploads, period PDF exports, computed insights, assistance drafts, and provider request contracts

All tests mock external providers at the boundary and do not require API keys.

Latest full workspace run: see `IMPLEMENTATION_STATUS.md` for the current result. This repository has no Playwright/Cypress setup or browser E2E test files. PostgreSQL migrations and local Evon inference were not live-verified.

### Provider Smoke Test

To verify live Gnani API connectivity (requires API keys configured in `.env`):

```bash
cd backend
python smoke_gnani.py
```

Exercises the Timbre → Prisma → Evon API pipeline with synthetic Hindi speech. Does not persist records. A 403 from the API is an access failure, not a success; the optional local Transformers route is documented above.

### Frontend

```bash
cd frontend
pnpm lint
pnpm build
```

## Disclaimer

This application contains worker-reported records. It does not independently verify employment status or unpaid wages and is not legal advice.
