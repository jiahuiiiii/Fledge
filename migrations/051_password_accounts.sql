-- Username/password sign-in for the test product (no email verification).
-- Only the local server role can read credentials and sessions.
CREATE TABLE password_credentials (
 account_id uuid PRIMARY KEY REFERENCES accounts ON DELETE CASCADE,
 username text NOT NULL UNIQUE CHECK(username ~ '^[a-z0-9_.-]{3,30}$'),
 password_hash text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE password_sessions (
 token_hash text PRIMARY KEY,
 account_id uuid NOT NULL REFERENCES password_credentials(account_id) ON DELETE CASCADE,
 created_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL
);
CREATE INDEX password_session_expiry ON password_sessions(expires_at);
CREATE TABLE password_attempts (
 key text PRIMARY KEY, window_start timestamptz NOT NULL, failures integer NOT NULL CHECK(failures>=0)
);
REVOKE ALL ON password_credentials,password_sessions,password_attempts FROM PUBLIC,thesis_app,thesis_source;
