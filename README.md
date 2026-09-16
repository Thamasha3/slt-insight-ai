# SLT insight.ai

Internal AI assistant for **SLT employees**. Employees log in, the backend
checks their **role** and **region**, retrieves only approved knowledge they
are allowed to see, and only then may call **Gemini 2.5 Flash**.

There is **one** knowledge base with three categories: **GENERAL**,
**REGIONAL**, and **CONFIDENTIAL_INTERNAL**.

Read `docs/how-auth-works.md`, `docs/knowledge-ingestion.md`,
`docs/retrieval.md`, and `docs/gemini-vertex.md`.

---

## What is in this repository

| Piece | Status |
|--------|--------|
| FastAPI backend | Working |
| React + Vite frontend | Login, dashboards, admin, knowledge, search, chat |
| MongoDB users, documents, chunks, chat, audit | Working |
| Register → pending → admin approve → login | Working |
| Four roles (Admin / Super / Regional / Normal) | Enforced on the API |
| Knowledge upload (Admin + Super User) | PDF, Word (.docx), CSV, Excel (.xlsx) |
| HITL document approval | PENDING is not searchable |
| Permission-aware search (`POST /retrieval/search`) | Working |
| Chat + Gemini (`POST /chat`) | Working (retrieval first) |

---

## Prerequisites

- Python **3.12** (recommended). Create the venv with `py -3.12`.
- Node.js 20+
- MongoDB on `localhost:27017`, or another URI in `.env`

MongoDB with Docker:

```powershell
docker run -d --name insight-mongo -p 27017:27017 mongo:7
```

---

## How to run

### 1. Backend

```powershell
cd E:\SLT\mnt\slt-insight-ai\backend

py -3.12 -m venv .venv
.\.venv\Scripts\activate

pip install -r requirements.txt
```

If `.env` is missing: `copy .env.example .env` then set:

- `JWT_SECRET_KEY` — a long random string
- `ADMIN_EMAIL_1` / `ADMIN_EMAIL_2` — local placeholders are fine for practice
- `GOOGLE_CLOUD_PROJECT=insighthub-508011`
- `GOOGLE_APPLICATION_CREDENTIALS` — full path to the Vertex JSON **outside** git

Create the first admin (email must match `ADMIN_EMAIL_1`):

```powershell
python scripts\bootstrap_admin.py
```

Default password: `ChangeMe123` (override with `BOOTSTRAP_ADMIN_PASSWORD`).

Start the API (keep this terminal open):

```powershell
uvicorn app.main:app --reload
```

Check:

- http://127.0.0.1:8000/health → `{"status":"ok"}`
- http://127.0.0.1:8000/docs

Tests:

```powershell
pytest -q
```

### 2. Frontend

Second terminal:

```powershell
cd E:\SLT\mnt\slt-insight-ai\frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

### 3. First-time walkthrough

1. Register an employee (login is blocked until approval).
2. Log in as `admin1@example.com` / `ChangeMe123`.
3. **Pending requests** → approve as NORMAL, REGIONAL, or SUPER.
4. **Knowledge** → upload `sample_data/general/sample_office_faq.csv` as GENERAL → **Approve**.
5. Log out, log in as the employee → **Chat** or **Search**.

Admin menus are hidden for other roles; `/admin/*` also returns **403** on the API.

---

## Security rules

- Passwords are bcrypt hashes. Secrets stay in `.env` (gitignored).
- ADMIN only for the two configured emails.
- Registration cannot set a role. Users cannot change their own role.
- `/admin/*` requires an active Admin.
- Retrieval and chat apply `chunk_is_visible_to`:
  - Normal → APPROVED GENERAL only
  - Regional → GENERAL + REGIONAL for **their** region
  - Super → GENERAL + all REGIONAL + CONFIDENTIAL_INTERNAL
  - Admin → no employee knowledge until SLT says otherwise
- If nothing authorized matches, chat returns **Insufficient Evidence** and **does not call Gemini**.
