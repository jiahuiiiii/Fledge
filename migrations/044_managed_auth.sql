-- Authentication material is accessible only to the local server role.
-- Source and ordinary application roles cannot select or mutate these tables.
CREATE TABLE auth_identities(
 project_url text NOT NULL, subject uuid NOT NULL,
 account_id uuid NOT NULL REFERENCES accounts ON DELETE CASCADE,
 verified_email text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(project_url,subject), UNIQUE(account_id)
);
CREATE TABLE auth_flows(
 token_hash text PRIMARY KEY, verifier text NOT NULL, email text NOT NULL,
 project_url text NOT NULL, expires_at timestamptz NOT NULL
);
CREATE TABLE auth_sessions(
 token_hash text PRIMARY KEY, project_url text NOT NULL, subject uuid NOT NULL,
 account_id uuid NOT NULL REFERENCES accounts ON DELETE CASCADE,
 access_token text NOT NULL, verified_at timestamptz NOT NULL,
 expires_at timestamptz NOT NULL,
 FOREIGN KEY(project_url,subject) REFERENCES auth_identities(project_url,subject) ON DELETE CASCADE
);
CREATE INDEX auth_session_expiry ON auth_sessions(expires_at);
CREATE TABLE auth_send_limits(
 key text PRIMARY KEY, window_start timestamptz NOT NULL, requests integer NOT NULL CHECK(requests>=0)
);
REVOKE ALL ON auth_identities,auth_flows,auth_sessions,auth_send_limits FROM PUBLIC,thesis_app,thesis_source;
