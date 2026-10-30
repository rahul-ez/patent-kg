# Authentication and ownership checklist

Implementation: October 18, 2026. Scope: local email/password accounts, secure
sessions, private analysis ownership, and account screens. Pipeline caching,
dependency upgrades, email delivery, and third-party identity providers are
separate work.

## Account and session security

- [x] Add nullable password hashes without granting access to pre-existing accounts.
- [x] Use Argon2id hashing; never store plaintext passwords or session cookies.
- [x] Add database-backed opaque sessions with expiry, rotation, and logout revocation.
- [x] Use HttpOnly, SameSite cookies, with configurable HTTPS-only delivery.
- [x] Protect mutations against CSRF and reject untrusted browser origins.
- [x] Add database-shared authentication throttling and bounded password hashing.
- [x] Return generic login errors, safe validation errors, and no-store API responses.

## Ownership

- [x] Derive case ownership from the authenticated session, never a submitted user ID.
- [x] Filter list, read, update, delete, run creation, and snapshot access by owner.
- [x] Check ownership before model calls and again inside persistence transactions.
- [x] Check embedded run IDs and use server snapshots for saved-run work.
- [x] Scope case-risk reports to the current user; leave patent corpus reports shared.
- [x] Preserve ownerless legacy cases and provide explicit local-operator assignment.

## Frontend

- [x] Add signup/sign-in screens matching the existing workspace design.
- [x] Protect intake, pipeline, and result routes; restore the session on refresh.
- [x] Add current-account display and sign-out controls.
- [x] Keep credentials out of local storage; retain CSRF only in memory.
- [x] Bind persisted draft/run pointers to one user and clear them on account changes.
- [x] Invalidate old responses/query caches on logout, expiry, or account switch.
- [x] Synchronize authentication changes across tabs and reject external return URLs.

## Verification

- [x] Apply and reapply the additive migration to the existing MySQL database.
- [x] Pass isolated authentication/ownership contract tests.
- [x] Pass two-account checks against real MySQL, including session revocation.
- [x] Pass existing persistence and live graph/database tests with explicit test owners.
- [x] Pass frontend state tests, TypeScript checking, and the production build.
- [x] Complete browser signup, private case/analysis, refresh, sign-out, and sign-in checks.
- [x] Record final evidence and remaining deployment limitations.

All scoped checks completed: 31 backend tests, 8 live auth tests, 3 live
integration tests, 3 persistence contracts, and 11 frontend state tests (56 total),
plus TypeScript/build and the real authenticated browser pipeline. A synthetic
browser account was signed out and removed with its single verification case;
existing ownerless cases and all patent data were preserved.

## Design decisions

Reuse the current cool paper/teal workspace palette: page `#F3F5F5`, white
surface `#FFFFFF`, ink `#26343A`, secondary text `#5B6870`, teal `#11675F`, and
hairline `#D9E0E2`. IBM Plex Sans remains the display/body font. The account
screen uses a left-aligned research/privacy explanation beside a single form;
on small screens the sections stack. There is no new marketing hero, animation,
or decorative dashboard. This preserves the project's current visual identity
and gives labels, keyboard focus, autocomplete, and actionable errors priority.

See [authentication documentation](../authentication.md) for setup and legacy cases.
