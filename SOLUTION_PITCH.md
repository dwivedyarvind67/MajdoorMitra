# MazdoorMitra: AI Voice-First Wage & Work Ledger for India's Informal Workforce

**Live Application:** [https://majdoormitra.vercel.app](https://majdoormitra.vercel.app)  
**Backend API & Docs:** [https://majdoormitra-production.up.railway.app/docs](https://majdoormitra-production.up.railway.app/docs)  
**Source Code (GitHub):** [https://github.com/dwivedyarvind67/MajdoorMitra](https://github.com/dwivedyarvind67/MajdoorMitra)  

---

### The Problem
India is home to over **450 million informal, daily-wage, construction, domestic, and migrant workers**. The majority face severe economic exploitation due to a systemic vulnerability:
- **Zero written contracts or proof of work:** Wage agreements are made verbally and settled on memory or fragmented scrap-paper notes.
- **Systematic wage theft and delays:** Contractors frequently dispute days worked, renegotiate agreed-upon rates after work completion, or fail to account for cash advances vs. final settlement.
- **Literacy and technological barriers:** Existing accounting software, spreadsheets, and complex smartphone apps are entirely inaccessible to workers who cannot read or write fluently.

### The Solution: MazdoorMitra
**MazdoorMitra (मज़दूरमित्र)** is a voice-first, AI-powered conversational wage ledger designed specifically for low-literacy informal workers. It enables workers to maintain an undisputed, audit-ready financial record simply by **speaking naturally in their native language (Hindi, Hinglish, and regional dialects)**.

---

### How It Works (3 Steps)
1. **Speak Naturally (Voice-First):**  
   The worker taps a single microphone button and speaks normally:  
   *“Sharma ji ke yahan 4 din kaam kiya, 600 rupay roz ki dihaadi aur 500 advance mila.”*  
   Gnani AI (Prisma STT) transcribes the speech into text.
2. **Deterministic Extraction & Review:**  
   Gnani Evon (LLM) extracts structured financial parameters (`days_worked: 4`, `daily_wage: 600`, `advance_received: 500`, `contractor: Sharma`). A defensive validation engine cross-checks constraints and prompts clarification questions for any missing variables.
3. **Worker Confirmation & Cryptographic Ledger:**  
   The worker verifies the simplified summary card with a single tap or voice response (*“Haan, sahi hai”*). Once confirmed, transactions are immutably logged into a persistent ledger. An audio receipt is spoken back using Gnani Timbre (TTS).

---

### Key Capabilities & Impact
- **Financial Precision:** Strict `Decimal` arithmetic with no floating-point rounding errors. Computes total earnings, advances, pending dues, and overpayments per contractor.
- **One-Tap Verifiable PDF Wage Statements:** Generates bilingual (Hindi + English) itemized wage slips with timestamps, contractor breakdowns, and original voice transcripts that can be shared via WhatsApp or presented in dispute resolutions.
- **Evidence Vault & Work Diary:** Attach worksite photos, physical receipt snapshots, and track daily attendance across multiple construction sites.
- **PIN-Based Authentication:** No email required; workers register and login using their mobile number and a 4-digit PIN.

### Architecture & Tech Stack
- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, persistent Hindi/English bilingual toggle (deployed on **Vercel**).
- **Backend:** FastAPI (Python 3.11), SQLAlchemy 2.0 (Async), Pydantic v2, PostgreSQL (deployed on **Railway**).
- **Speech & Reasoning AI:** Gnani Prisma (STT), Gnani Evon (Reasoning/Extraction), Gnani Timbre (TTS).
- **Documentation Engine:** ReportLab bilingual A4 statement generation.

---
*MazdoorMitra transforms ephemeral verbal agreements into verifiable, worker-owned economic power.*
