# Knowledge upload and ingestion (Phases 5–6)

## What this phase does

Admin or Super User can upload a **PDF**, **Word (.docx)**, **CSV**, or
**Excel (.xlsx)**, choose a **category**
(and a **region** when the category is REGIONAL), and the backend:

1. Checks that the caller is an **active Admin or Super User**.
2. Stores the file under `backend/uploads/` (gitignored).
3. Extracts content:
   - PDF: text **page by page** with PyMuPDF
   - Word: paragraphs plus labeled table rows
   - CSV / Excel: each **row** becomes a labeled record (`Column: value`)
4. Splits long text into **chunks**.
5. Saves citation metadata (`filename`, `source_page`, `sheet_name`, `source_row`).
6. Leaves the document **PENDING**.

Employees cannot see PENDING text in retrieval. After Admin or Super User
**Approve**, chunk `status` becomes **APPROVED**. Gemini is still **not** called
during upload.

```
Upload file
  → validate + save
  → extract (PDF pages or table rows)
  → chunk
  → PENDING (not searchable)
  → Admin or Super User approve
  → APPROVED (ready for Phase 7 retrieval)
```

## Why tables are not dumped as one paragraph

CSV and Excel already have columns. Turning a row into
`Galle,08:00-16:00` loses meaning. The extractor stores:

```text
Sheet: Southern
Record: 2
Office: Galle
Hours: 08:00-16:00
```

so later citations can say **file + sheet + row**.

## Scanned PDFs

If a PDF is only images, extraction finds no text and the document is
**FAILED**. OCR is **optional** (not Phase 1) until SLT requires scanned-document
ingestion and provides an on-prem OCR approach.

## Word (.docx)

Upload **.docx**. Legacy `.doc` is not supported.

## Legacy .xls

Upload **.xlsx**. Old `.xls` is rejected with a clear error.

## How to test

1. Log in as Admin or Super User.
2. Open **Knowledge**.
3. Upload `sample_data/general/sample_office_faq.csv` as GENERAL, or
   `sample_data/general/sample_leave_policy.docx`.
4. Expected: status `PENDING`, chunk count ≥ 1, preview shows `Topic:` labels.
5. Approve. Status becomes `APPROVED`.
6. Log in as a Normal user and open `/admin/knowledge` — the menu is hidden
   and the API returns **403**.
7. Log in as Normal and open **Search**, ask about leave — you should see the
   general FAQ. Ask about Galle hours after uploading the Southern CSV as
   REGIONAL/SOUTHERN — Normal should see **Insufficient Evidence**; a Southern
   Regional user should see it after approval.
