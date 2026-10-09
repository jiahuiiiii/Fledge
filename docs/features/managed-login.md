# Managed email login

Implemented 9 October 2026. Supabase verifies email identity; the existing private PostgreSQL database stores research. The app remains bound to `127.0.0.1`; this change does not publish it or provide remote participant access.

## Configuration and sign-in

Set `SUPABASE_URL` to the project API URL (`https://<project-ref>.supabase.co`), `SUPABASE_PUBLISHABLE_KEY` (or legacy `SUPABASE_ANON_KEY`) and `THESIS_OWNER_EMAIL` in the private `.env`. A dashboard URL is not an API URL. No database password or service-role key is needed. Partial configuration fails closed.

Supabase Auth URL Configuration uses Site URL `http://127.0.0.1:8841` and allowed redirect `http://127.0.0.1:8841/auth/callback`. `THESIS_AUTH_SITE_URL` can configure another loopback installation address; its exact callback must be allowed in Supabase. Email sign-in is enabled. Google remains disabled until separately configured.

Request a link from the app and open the newest email in the same browser/device. The server implements Supabase PKCE, consumes a short-lived flow once, exchanges the code, then verifies the access token through `/auth/v1/user`. It requires a confirmed, non-anonymous email matching the requested address. Client JWT claims and client-supplied owner IDs cannot grant access.

The first verified identity matching `THESIS_OWNER_EMAIL` links to the existing installation account. It preserves existing research rather than copying or resetting it. A second subject cannot reclaim that account by matching the configured email. Other verified users receive separate internal accounts; an existing subject retains its original mapping.

Supabase's default email service may restrict recipients to project-team addresses. Other participant emails require an appropriately configured email service or separately enabled provider. The project/key settings check does not prove email delivery.

## Sessions and isolation

The browser receives a random HttpOnly, SameSite Strict session cookie. Only its SHA-256 digest is stored as the lookup key. Access tokens, flow verifiers and identity mappings stay in server-only tables; the application and source database roles cannot read them. The database and backups remain private to this OS account. This is not protection against the installation's OS administrator.

New sign-ins with a provider refresh token last at most seven days. Access tokens keep their original at-most-one-hour lifetime and renew within 60 seconds of expiry under a session lock. Renewal verifies the returned identity and rotates both server-only tokens without extending absolute session expiry. Pre-upgrade sessions retain their original expiry and need a fresh sign-in for renewal. Identity is also checked every minute. Provider outages deny requests with retryable errors while keeping the local session; invalid/revoked/expired/wrong-subject sessions cannot access research. Logout deletes the session. Private UI unmounts on logout/401. Same-origin and mutation-header checks remain; tokens are never exposed in responses or logs.

The Account menu identifies the verified email. Focus checks and account-labelled responses detect another tab's account change. Expected-account headers are compared to server-verified identity, rejecting mismatches before private writes/logout; they cannot authenticate or select an account. Hidden-company preferences are account-scoped; only the installation owner adopts its old browser preference.

Email requests retain one/minute/address and ten/hour/installation limits. Resend countdowns prevent accidental repeats. Supabase's delivery limits are separate and unknown reset times remain unknown. See [recovery and isolation verification](../reviews/2026-10-09/session-recovery-and-account-isolation.md).

Every private API uses the authenticated internal account for forced database row isolation, including research questions, ideas, valuations, alert reviews, weekly reviews, loading, exports, peer selections and Telegram settings. Shared original-source evidence and supported public business briefs remain shared. The original global AI ledger and cumulative US$30 installation cap remain shared; signing up creates no new allowance.

Background workers retain explicit account scopes. They process the installation owner and identities linked to the configured project; historical QA accounts are not automatically enrolled. Existing enabled owner watches continue while the local app runs. Signing in does not enable a watch or add a Telegram recipient.

## Recovery

Migration 044 adds authentication tables without rewriting existing research. The ordered migration runner applies pending upgrades transactionally. Before installation, a full private database/configuration backup was taken; its recovery was verified in an independent temporary cluster, with all 100 original table fingerprints matching.

For an operator rollback of login alone, set `THESIS_AUTH_ENABLED=false` in the private `.env`, restart the loopback app and reload the browser. This restores the earlier local owner access mode without deleting identity mappings or research. Keep the existing Supabase fields intact so login can be re-enabled. Use this only for this local installation, not as a public-server login fallback. The default is managed login when the required settings are present.

The actual backup path and restoration evidence are recorded in the [phase review](../reviews/2026-10-09/original-research-and-managed-login.md). Do not restore an old full database casually: it would discard work saved after that backup. Prefer the login-only switch when the problem concerns login.

## Verification limits

Controlled provider-response tests cover PKCE, confirmation, owner linking, two-account API/RLS isolation, expiry, failed verification, logout, flow replay, CSRF, server-only token tables and operator rollback. A guarded browser journey verifies the sign-in form without sending an email. The owner subsequently completed two real verified sign-ins: one linked to the existing owner and one to a separate account. The signed-in local workspace was also inspected read-only. This proves those configured identities worked; it does not establish delivery to every participant address or universal provider availability.

Primary references: [Supabase PKCE](https://supabase.com/docs/guides/auth/sessions/pkce-flow), [passwordless email](https://supabase.com/docs/guides/auth/auth-email-passwordless), [redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls).
