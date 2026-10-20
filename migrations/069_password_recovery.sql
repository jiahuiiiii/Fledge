-- Password reset without email: each username account can hold one recovery
-- code, stored only as a scrypt hash like the password. Using it replaces the
-- password and issues a new code; it is never shown again after creation.
ALTER TABLE password_credentials
 ADD COLUMN recovery_hash text,
 ADD COLUMN recovery_set_at timestamptz;
