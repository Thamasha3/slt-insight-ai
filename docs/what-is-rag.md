# What is RAG? (plain language)

**RAG** means Retrieval-Augmented Generation.

A normal chatbot does this:

```
question → Gemini → answer
```

Gemini would guess from its general training. That is unsafe for SLT:
it might invent policy, or mix in facts a Normal User must not see.

RAG does this:

```
question
  → identify the logged-in employee (role + region)
  → search only APPROVED documents that person may see
  → copy the matching snippets into a prompt
  → Gemini writes an answer using those snippets
  → show the answer plus real filenames/pages
```

Think of three filing cabinets:

1. **GENERAL** — every employee
2. **REGIONAL** — only that region (and Super Users)
3. **CONFIDENTIAL_INTERNAL** — Super Users only

Vector search can replace the keyword ranker later without changing this
permission model. See `docs/retrieval.md`.
