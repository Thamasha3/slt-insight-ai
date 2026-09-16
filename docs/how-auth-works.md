# How authentication and RBAC work (simple explanation)

## Why we start here (not with Gemini)

If we connected Gemini first, anyone who could reach the API could ask
questions and the model might answer from general knowledge **or** from
documents it should not see.

Instead:

1. Prove who the user is (login → JWT).
2. Look up their **role** and **region** in MongoDB.
3. Only then (later phases) retrieve documents they are allowed to see.
4. Only then send that text to Gemini.

The LLM never decides permissions. The backend does.

## Roles (four only)

| Role       | Meaning |
|------------|---------|
| ADMIN      | System administrator. Not the same as Super User. |
| SUPER      | Highest **information** access, plus knowledge upload/validation (not user admin). |
| REGIONAL   | General + their assigned region only. |
| NORMAL     | General data only. |

## Account lifecycle

```
Register  →  PENDING  →  Admin Approve  →  ACTIVE  →  can log in
                  ↘  Admin Reject  →  REJECTED
ACTIVE  →  Admin deactivate  →  DEACTIVATED
```

Self-registration **cannot** set role to ADMIN. New accounts are stored
as `NORMAL` + `PENDING`. The Admin chooses the real role at approval.

## Admin emails

Only two emails (from `.env`: `ADMIN_EMAIL_1`, `ADMIN_EMAIL_2`) may ever
have `role=ADMIN`. That check happens in the backend, not in React.

## JWT vs database

The login response includes a JWT (a signed token). For every protected
request we:

1. Verify the token signature.
2. Load the user **again from MongoDB**.

That way, if an Admin deactivates someone, the old token stops working
immediately.

## Collections created now

`users`, `documents`, `document_chunks`, `knowledge_sources`,
`approval_records`, `chat_sessions`, `chat_messages`, `audit_logs`.

Only `users` and `audit_logs` are used heavily in Phases 1–4.
The others exist so later phases have a consistent database shape.
