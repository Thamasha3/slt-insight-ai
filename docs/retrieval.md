# Permission-aware retrieval (Phase 7)

This is **not** the chatbot yet. It is the filing-cabinet search that will
later sit in front of Gemini.

```
question
  → login token
  → load role + region from MongoDB
  → keep only APPROVED chunks that role may see
  → rank with keyword overlap
  → return snippets + citations
```

Gemini is **not** in this path. That is intentional: if retrieval is wrong,
we must not send extra text to an LLM.

## Who sees what

| Role | Search results |
|---|---|
| Normal | APPROVED `GENERAL` only |
| Regional | APPROVED `GENERAL` + `REGIONAL` for **their region** |
| Super | APPROVED `GENERAL` + all `REGIONAL` + `CONFIDENTIAL_INTERNAL` |
| Admin | **None** until SLT defines Admin chat access |

React hiding a menu is not enough. `POST /retrieval/search` applies the same
`chunk_is_visible_to` rules used in tests.

## Ranking (temporary)

This phase uses **keyword overlap**, not embeddings. That is enough to prove
RBAC. Vector search can replace the ranker later **without** changing the
permission filter.

## How to test

```powershell
# after Admin approved a GENERAL PDF/CSV
curl -X POST http://127.0.0.1:8000/retrieval/search -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d "{\"query\":\"annual leave\"}"
```

- Normal user + confidential query → `insufficient_evidence: true`
- Regional SOUTHERN + Western hours → no Western snippets
- Super user + confidential query → matching confidential snippets
- Pending documents → never returned

UI: log in as an employee → **Search**.
