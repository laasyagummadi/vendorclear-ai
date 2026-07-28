# Role-Based Access Control — added 22 July (catching up 20 July / Day 1 scope)

## What was missing
The sprint plan lists **Role-based access** as a Laasya Day-1 (20 July)
deliverable — Feature 7 in the vision doc: Admin / Analyst / Vendor / Auditor,
each with different permissions. The codebase only had a single `is_admin`
boolean on `User`, and **no route enforced it at all** — any logged-in user
(including a brand-new self-registered account) could delete vendors or
rewrite compliance policies.

## What changed

**Backend**
- `app/models/user.py` — new `UserRole` enum (`ADMIN`, `ANALYST`, `VENDOR`,
  `AUDITOR`) and a `role` column on `User`. `is_admin` is kept for backward
  compatibility but is now derived from `role`.
- `app/utils/rbac.py` (new) — `get_current_user` (resolves the full `User`
  row) and `require_roles(*roles)` dependency factory for gating routes.
- Routes gated to match the Feature 7 permission table:
  | Endpoint | Allowed roles |
  |---|---|
  | `POST/PATCH/DELETE /policies` | ADMIN only |
  | `POST/PATCH /vendors` | ADMIN, ANALYST |
  | `DELETE /vendors/{id}` | ADMIN only |
  | `POST /vendors/{id}/documents` (upload) | ADMIN, ANALYST, VENDOR |
  | Everything else (GET/list/reports/alerts) | any authenticated role — this is how Auditor gets read-only, whole-system visibility |
- `alembic/versions/888ff8141fd1_add_user_role.py` — migration adding the
  `role` column and backfilling `ADMIN` for any existing `is_admin=true` row.
- `scripts/seed_data.py` — seeds one demo login per role so all four can be
  demoed immediately (see below). The dev `vendorclear.db` was reset so it
  rebuilds with the new column on next run — it only held reproducible seed
  data.
- Self-registration (`POST /auth/register`) always creates an `ANALYST`
  account — the public sign-up form can't grant itself Admin or Auditor.

**Frontend**
- The logged-in user's role now flows into every page (`App.jsx`).
- Sidebar shows a role badge.
- "Add Vendor" (Vendors page) and "Edit"/"Upload Document" (Vendor detail
  page) are hidden for roles that the backend would reject anyway — this
  is a UI convenience, the backend is the actual enforcement point.

## Demo logins (password `DemoPass123` for all)
| Role | Email |
|---|---|
| Admin | demo@vendorclear.ai |
| Analyst | nirupama@vendorclear.ai / hruthi@vendorclear.ai |
| Vendor | vendor.demo@vendorclear.ai |
| Auditor | auditor.demo@vendorclear.ai |

## Known scope limits (flagging honestly, not hiding them)
- "Vendor: view own compliance" is not yet scoped to a specific vendor
  record — there's no vendor↔user linkage in the data model yet, so a
  VENDOR-role account can currently see all vendors, same as everyone else.
  Narrowing that is a bigger feature (needs a `Vendor.owner_user_id` or
  similar) and is a good candidate for a later sprint day rather than
  squeezed into this pass.
- No admin UI to change a user's role after creation yet (Feature 6's
  "Admin Portal" is documented as later-day scope) — for now it's a direct
  DB/API-level change.
