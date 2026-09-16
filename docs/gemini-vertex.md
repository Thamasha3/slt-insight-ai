# Gemini / Vertex AI (Phase 8)

SLT asked for **Gemini 2.5 Flash** with **location = global**. The backend
calls Vertex AI. React never sees the service-account JSON.

## Security order (do not reverse)

```
question
  → JWT + MongoDB role/region
  → keep only APPROVED chunks this role may see
  → if none: reply "Insufficient Evidence" (Gemini is not called)
  → if some: send only those snippets to Gemini
```

Unauthorized, PENDING, REJECTED, and other-region text never enter the
prompt. Gemini does not decide permissions.

## Credentials

Keep the JSON **outside** this repository (already true for
`E:\SLT\insighthub-508011-07661ff96faf.json`). In `backend/.env`:

```
GEMINI_MODEL=gemini-2.5-flash
GEMINI_LOCATION=global
GOOGLE_CLOUD_PROJECT=insighthub-508011
GOOGLE_APPLICATION_CREDENTIALS=E:\SLT\insighthub-508011-07661ff96faf.json
```

Never commit that file. Never put it in the frontend.

The service account needs Vertex AI User (or equivalent) on the project.

## How to test

1. Approve a GENERAL sample document.
2. Log in as Normal. Chat about that topic → Gemini is called; citations
   are GENERAL only.
3. Ask about confidential or another region → `Insufficient Evidence`,
   and `gemini_called` is false.
4. Super User asking a confidential question may receive confidential
   snippets in the prompt.

API: `POST /chat` with `{ "query": "..." }`.
