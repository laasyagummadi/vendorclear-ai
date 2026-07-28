# Compliance Service Fixes - Completed

## Errors Fixed
- [x] Fix 1: Unhandled `ValueError` in `get_compliance_report()` for `expiry_flag` — wrapped `date.fromisoformat()` in `_any_expired()` helper with try/except
- [x] Fix 2: `expiry_flag` only checked `gl_expiry`, ignored `wc_expiry` — now checks both via `_any_expired(v.gl_expiry, v.wc_expiry, today=date.today())`
- [x] Fix 3: `_any_expired()` keyword-only argument `today` was being passed positionally — changed to `today=date.today()` to avoid `TypeError` at runtime
- [x] Fix 4: Indentation break in `compute_vendor_score()` — `findings_result` query and all subsequent code was at module level (column 0) instead of method level (8 spaces), causing `SyntaxError: 'await' outside function`. Also moved `vendor = await self.db.get(...)` outside the for loop.
- [x] Syntax verified (no errors)

