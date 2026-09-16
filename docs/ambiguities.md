# Open questions for SLT (do not invent answers)

These items are **not decided in code**. Until SLT confirms them, the
implementation uses the conservative default listed under each item.

## 1. Admin knowledge retrieval (chat)

The permission matrix says Admin access to General / Regional /
Confidential data is **"Controlled separately"**.

**Current default:** Admin can **manage** users and (with Super User) knowledge
sources. Admin is **not** treated as a Super User for chat retrieval.
`allowed_categories_for(ADMIN)` currently returns an empty set so the
chat path cannot silently leak knowledge until SLT defines Admin chat
access.

## 2. Super User management of other users

The matrix says Super User may manage users / approvals / knowledge /
audit logs **"According to SLT policy"**.

**Current default:**
- **Knowledge validation** is shared: Super User and Admin may upload,
  preview, approve, and reject documents. Permanent document deletion
  remains **Admin-only**.
- **User administration** (create / approve accounts / roles / deactivate)
  and **audit-log access/export** remain **Admin-only**.
- Super User is not a system administrator.

## 3. Official SLT region list

The `Region` enum is **sample data** (WESTERN, SOUTHERN, NORTHERN,
EASTERN, CENTRAL). Replace with SLT's real region names when provided.

## 4. Confidential documents and region

The spec does not say whether `CONFIDENTIAL_INTERNAL` documents may also
have a region. **Current default:** region is optional; Super User can
retrieve confidential documents regardless of region.

## 5. Document approval workflow

The spec allows PENDING → APPROVED. **Current default (Phase 6+):**
uploads start as PENDING and are not retrievable until an Admin or Super User
approves them.

## 6. First Admin bootstrap

Self-registration cannot create an Admin. The first Admin must be
provisioned using `backend/scripts/bootstrap_admin.py` with an email
that matches `ADMIN_EMAIL_1` or `ADMIN_EMAIL_2`.

## 7. Corporate SSO

The BRD calls for SLT corporate SSO. This phase keeps local email/password
JWT auth. SSO is **not** implemented here because tenant IDs, IdP metadata,
and callback URLs have not been provided. Do not remove local login until
a migration plan exists.

## 8. On-premises AI / data privacy

Vertex AI Gemini 2.5 Flash remains the configured model (as previously
specified). An on-prem LLM would require SLT-hosted GPU/inference, network
policy, and a replacement client. That is infrastructure, not an app toggle.

## 9. User deletion

Accounts are **deactivated**, not physically deleted, so audit logs and
chat history keep a stable `user_id`. Hard delete is not enabled.

## 10. Regional KPI dashboards

Phase 1 has Admin operations counts (users/documents), not invented regional
KPI charts. Metric definitions and source systems are needed from SLT.

## 11. Three knowledge bases

Logical categories (`GENERAL`, `REGIONAL`, `CONFIDENTIAL_INTERNAL`) in one
MongoDB database, with RBAC filters. Physically separate databases are not
created unless SLT requires isolation at the storage layer.
