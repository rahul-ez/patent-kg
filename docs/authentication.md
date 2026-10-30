# Authentication and analysis ownership

The application uses local email/password accounts and MySQL-backed sessions.
The patent corpus, graph, and vector index remain shared reference data. Ideas,
case history, saved runs, evaluations, and improvements belong to one user.

## Setup

For the already-populated database, from the repository root:

```powershell
venv/Scripts/python.exe -m pip install -r backend/requirements.txt
venv/Scripts/python.exe backend/scripts/database/migrate_auth.py
```

The migration adds `app_users.password_hash`, `auth_sessions`, and
`auth_rate_limits`. It does not reimport patents, delete analyses, change owners,
or create an administrator. A repeat application is safe. Existing users with
no password hash cannot sign in until a trusted operator provisions credentials;
signup does not claim those accounts by matching their email.

Fresh Compose databases execute `database/sql/05_auth.sql` after the base schema.
Existing Docker volumes do not rerun initialization scripts: run the Python
migration. It needs schema-changing database privileges; the running API needs
the usual application CRUD permissions. No database or graph rebuild is needed.

Start the normal backend and frontend, then open `/signup` to create your own
account. Registration signs you in and opens the requested workspace route (or
Saved cases). A new account begins with no private cases. Sign in later at
`/login`; logout is available in the shared app header.

## Sessions and request protection

- Passwords use pwdlib's recommended Argon2id hasher, including hash upgrades
  on successful login. Signup accepts 15–128 characters, including spaces;
  passwords are never trimmed or written to browser storage.
- A session is a 32-byte cryptographically random opaque cookie. Only its
  SHA-256 digest is stored in MySQL. Login issues a fresh session and revokes
  the previous cookie session; other device sessions remain independent.
- Cookies are host-only, HttpOnly, SameSite=Lax, and restricted to `/api`.
  Sessions expire after 12 hours by default, with a configurable 1–168-hour
  lifetime. The database checks expiry and active-account status on each request.
- The frontend gets a session-bound CSRF value from `/auth/me` and keeps it only
  in memory. Authenticated POST/PATCH/DELETE requests require `X-CSRF-Token`.
  Login/signup require JSON and the `X-Requested-With: patent-client` header.
  Browser Origin values must match the configured allowlist. CLI clients may
  omit Origin but must still satisfy the relevant headers and session checks.
- Login/signup attempts use atomic, shared database counters for IP and email
  buckets. Login permits 30 requests/IP and 10/email per 15-minute window;
  signup permits 10/IP per hour and 10/email per 15 minutes. At most four password
  hashes/verifications run concurrently per API process. The limiter uses the
  server's client address, not forwarding headers parsed by application code.
- Login failure messages do not distinguish unknown users, wrong passwords,
  inactive users, or users without credentials. Request validation does not echo
  the rejected password. API responses are marked `Cache-Control: no-store`.

### Environment

```dotenv
SESSION_COOKIE_SECURE=false
SESSION_HOURS=12
APP_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174
```

`false` is for loopback HTTP development only. Before deployment, require HTTPS,
set `SESSION_COOKIE_SECURE=true`, and replace `APP_ORIGINS` with exact trusted
HTTPS origins. Serve frontend and `/api` under one origin (as the Vite development
proxy does). No wildcard CORS origins or frontend local-storage bearer tokens
are needed. Keep hostname usage consistent: `localhost` and `127.0.0.1` have
different cookie/storage scopes. Changing the allowed origins requires an API
restart. Do not expose the development server publicly.

If using a reverse proxy, configure its trusted forwarding behavior and ensure
untrusted clients cannot bypass it or supply trusted forwarded addresses.
Add deployment-level request limits and HTTPS/security headers. Periodically
purge expired session records and old rate-limit buckets under an operator's
maintenance policy. Authentication does not resolve dependency advisories or
replace a production security review.

## API

| Endpoint | Behaviour |
|---|---|
| `POST /api/auth/signup` | Validate account details, hash password, create a session |
| `POST /api/auth/login` | Verify credentials and rotate the cookie session |
| `GET /api/auth/me` | Return current user, session expiry, and CSRF value; 401 when signed out |
| `POST /api/auth/logout` | Require CSRF, revoke current session, and expire its cookie |
| `/api/cases` and case/run routes | Require sign-in and scope private records to that account |
| `/api/pipeline/run`, `/api/evaluate*`, `/api/improve` | Require sign-in; check referenced case/run ownership before model work |
| `/api/kg/*`, `/api/reports/*` | Require sign-in; case-risk report is owner-filtered, patent statistics remain shared |

`/api/health` and documentation endpoints remain public. Authentication failures
return 401, CSRF/origin failures 403, inaccessible case/run IDs 404, throttling
429, and unavailable account storage 503. No auth-disabled option exists in the
production application. Test apps explicitly override dependencies only inside
test setup; `serve_unsaved_fixture.py` is a synthetic failure server, never a
production route or account service.

Repository functions require an explicit owner ID, and their SQL includes the
owner predicate. Case creation derives it from the principal. For saved-run
evaluation/improvements, the server verifies top-level and embedded IDs and
uses the stored idea, retrieval snapshot, and evaluation rather than accepting
client replacements as authoritative. Persistence checks ownership again under
a row lock. Shared corpus queries never expose private invention text.

## Existing ownerless cases

Legacy cases are preserved but hidden from all normal accounts. They are not
assigned to the first signup and cannot be claimed through an API request.
After verifying the intended owner, a trusted local project operator can run:

```powershell
venv/Scripts/python.exe backend/scripts/database/assign_case_owner.py --list-unowned
venv/Scripts/python.exe backend/scripts/database/assign_case_owner.py --case-id CASE_UUID --owner-email owner@example.com
```

Only the explicitly named ownerless case is changed, in a transaction. The
target must be an active registered account with a password hash. Already-owned
cases are refused. Do not assign old research based solely on an unverified
signup email; verify the person and the case out of band.

## Browser isolation

Route guards check the session before rendering private pages. Local storage
keeps a user ID plus that user's draft/run pointer, never credentials or full
results. Version-one browser state is discarded because its owner is unknown.
Refreshing with the same authenticated user can restore a saved run from MySQL.
Logout, expiry, and account switching clear draft/result state and query caches.
Every request carries a local epoch so a response from an earlier sign-in cannot
repopulate the current user's screen. Cross-tab auth events invalidate other
tabs too. Post-login return paths are restricted to known internal workspace
routes. No persistent client-side cookie/token access is required.

## Verification and limits

See the [checklist](planning/auth-checklist.md) and
[verification report](reports/auth-verification.md). The real-database suite
creates two temporary accounts and verifies private case/report isolation,
embedded run IDs, direct-write ownership, logout revocation, expired/disabled
sessions, hashed secrets, throttling, and explicit orphan-case assignment.
It deletes only its own temporary records.

Password reset, email verification, MFA, social login, account deletion, and
administrative user-management screens are not included. No verification email
is sent. Existing database roles are not an app-level administrator bypass.
Session cookies protect transport under HTTPS; private invention text is not
application-level encrypted in MySQL. Model accuracy and pipeline caching remain
separate concerns.
