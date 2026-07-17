# ─────────────────────────────────────────────────────────────
#  app/utils/rate_limit.py  —  Shared slowapi Limiter instance
# ─────────────────────────────────────────────────────────────
# NOTE: previously the Limiter was instantiated inline in main.py and wired
# into app.state + the RateLimitExceeded exception handler, but no route
# anywhere actually used @limiter.limit(...). That made the whole rate-limit
# stack inert — /auth/login had no brute-force protection, /auth/register
# had no signup-spam protection, and document upload had no abuse
# protection, despite RATE_LIMIT_PER_MINUTE being configured in settings
# and looking like it was doing something. Moved to a shared module so
# route files can import and apply it, and applied it to the sensitive
# endpoints below.
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
