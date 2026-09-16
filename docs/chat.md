# Chat (Phase 9)

`POST /chat` creates or continues a session owned by the logged-in user.

The endpoint behaves like a chatbot:

- Greetings and “what can you do?” get a local reply (Gemini is not called).
- Factual questions retrieve **approved** chunks for that role, then Gemini
  answers from those snippets only.
- Follow-up questions reuse the same `session_id` and earlier user turns for
  search, so “tell me more about that” still finds the previous topic.
- Chat `citations` include only snippets the answer actually marked as `[n]`.
  Unused retrieved chunks are not returned.

Another employee cannot list or read those messages (404).

Admin can use the chat UI for greetings. Admin knowledge retrieval stays
empty until SLT defines Admin knowledge access (`docs/ambiguities.md`).
