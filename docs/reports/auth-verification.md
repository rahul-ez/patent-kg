# Authentication and ownership verification

Verified October 18, 2026. See the [authentication guide](../authentication.md)
and [implementation checklist](../planning/auth-checklist.md).

## Implemented

- Signup/login with Argon2id password hashes and normalized email addresses.
- Expiring, rotating, server-revocable sessions in HttpOnly/SameSite cookies;
  MySQL stores only token hashes. HTTPS-only cookies are configurable.
- Session-bound CSRF checks, exact-origin allowlisting, safe validation errors,
  no-store API responses, shared login throttling, and bounded hash concurrency.
- Explicit ownership in private repository queries and writes. Foreign and
  ownerless case/run IDs return 404, including embedded IDs. Model calls are
  preceded by ownership checks; transactional writes check again.
- Server snapshots are authoritative for saved-run evaluation/improvements.
  Client-provided user IDs or replacement saved results cannot transfer ownership.
- Protected frontend routes, signup/sign-in forms, account display, and logout.
  Local storage has a user-scoped draft/run pointer, never credentials or results.
  Account boundaries clear private state/caches and invalidate old responses.
- Additive migration and an explicit local operator tool for legacy-case ownership.

## Checks

| Check | Result |
|---|---|
| Backend unit/contract tests | 31 passed, including 14 authentication boundary tests |
| Live MySQL authentication tests | 8 passed with two temporary accounts |
| Existing live MySQL/Neo4j tests | 3 passed with explicit temporary owners |
| Existing persistence contracts | 3 passed |
| Frontend state tests | 11 passed, including account switching, expiry epochs, and safe return paths |
| TypeScript and production build | Passed |
| Additive migration | Applied and reapplied successfully to the populated database |
| Browser signup | Created a synthetic local account; protected intake opened after signup |
| Browser ownership | New account did not see legacy cases; its own draft saved and survived refresh |
| Live authenticated analysis | Real Gemini/PatentSBERTa/FAISS/Neo4j/GraphSAGE pipeline completed and saved 94 grouped results |
| Live evaluation/improvements | Both completed and saved under the authenticated run |
| Logout and re-login | Logout cleared private UI; re-login listed the account's case and reopened the saved snapshot |
| Cross-tab logout | Both local verification tabs returned to login |

The automated suites total **56 passing tests**. Authentication contract tests
use explicit mocks where isolation is intended; live authentication tests use
the real database/session/password code. Their pipeline payloads are clearly
labelled fixtures to avoid AI costs during security checks. Separately, the
browser pipeline/evaluation/improvement flow used actual services and models.
Only fast-mode evaluation was exercised live.

The live database suite verifies that a second user cannot list, read, update,
delete, append a run, evaluate, improve, or report on the first user's private
research. It also checks nested run-ID attacks, direct persistence writes,
Argon2id hashes, hashed session storage, captured-cookie revocation, expired and
disabled sessions, atomic throttling, and deliberate orphan-case assignment.

Original ownerless cases were not assigned or deleted. Patent publications,
graph relationships, and vector artifacts were not rebuilt or changed for this
feature. Automated checks remove only their own UUID records; the disposable
browser verification account/case are also removed after verification. Live
test passwords were randomly generated, not saved to source or offered as
user credentials. Static strings in isolated unit tests do not authenticate
any live account.

## Repeat checks

From the repository root in PowerShell:

```powershell
venv/Scripts/python.exe -m unittest discover -s backend/tests -v
$env:RUN_DATABASE_TESTS = '1'
venv/Scripts/python.exe -m unittest discover -s tests -p test_live_auth.py -v
venv/Scripts/python.exe -m unittest discover -s tests -p test_live_integration.py -v
venv/Scripts/python.exe -m unittest discover -s tests -p test_persistence_contract.py -v
Remove-Item Env:RUN_DATABASE_TESTS
cd frontend
npm test
npm run build
```

Apply the auth migration first, and use local `.env` database settings. Live
tests create temporary accounts/cases and remove only their own records. They
do not need to claim a real legacy case. Frontend tests use Node 24 or newer.

## Deployment and remaining scope

- Set HTTPS-only cookies and exact trusted HTTPS origins before exposing the app.
  The local server is loopback-only; development HTTP cookie settings are not a
  production configuration. Configure proxy trust and request limits deliberately.
- Email verification, password recovery, MFA, social login, account deletion,
  and admin-management screens are not part of this change. Signup does not
  send email or verify control of the mailbox. Legacy case assignment therefore
  requires out-of-band identity verification by the trusted project operator.
- Existing passwordless user rows remain passwordless and cannot sign in.
  No matching-email takeover or automatic first-user administrator is introduced.
- SQL DDL commits implicitly; migration is additive/repeatable, not an atomic
  all-or-nothing DDL rollback. Fresh initialization and existing-volume migration
  are separate paths. Existing runtime account permissions may need an operator
  with schema privileges for migration.
- The earlier dependency advisories, pipeline latency, model quality/calibration,
  and deep reconstruction testing remain separate work. This is not a security
  audit or a production-readiness certification. Review existing ML/debug logging
  before deployment because it can contain invention descriptions.
- Desktop browser rendering and functional account flows were checked. Mobile
  stacking CSS is provided; a full mobile-device/browser matrix was not tested.

Local screenshot evidence: `artifacts/verification/auth-login.jpg` (ignored by Git).
