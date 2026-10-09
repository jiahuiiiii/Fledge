-- Existing sessions retain their original expiry; renewal starts only after a
-- new provider-verified sign-in that supplies a refresh token.
ALTER TABLE auth_sessions ADD COLUMN refresh_token text;
ALTER TABLE auth_sessions ADD COLUMN access_expires_at timestamptz;
UPDATE auth_sessions SET access_expires_at=expires_at;
ALTER TABLE auth_sessions ALTER COLUMN access_expires_at SET NOT NULL;
REVOKE ALL ON auth_sessions FROM PUBLIC,thesis_app,thesis_source;
