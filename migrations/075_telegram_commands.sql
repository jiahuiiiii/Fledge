-- Durable record of each command received from a linked Telegram chat.
-- Written before any reply is sent, so a crash never repeats a reply or a
-- paid explanation: one row per bot update (update_key is unique). Only the
-- command name and a validated ticker are kept, never the raw message text.
-- Slow commands (explain) are queued here and finished by a worker that saves
-- the result and this row's 'done' state in one transaction.
-- Owner approved 31 October 2026 (draggable workspace and Telegram commands
-- plan, Feature B).
CREATE TABLE telegram_commands (
 id uuid PRIMARY KEY,
 owner_id uuid NOT NULL REFERENCES accounts ON DELETE CASCADE,
 update_key text NOT NULL UNIQUE CHECK(length(update_key) BETWEEN 3 AND 120),
 command text NOT NULL CHECK(command IN ('help','today','why','world','explain','watch')),
 argument text CHECK(argument IS NULL OR argument ~ '^[A-Z][A-Z0-9.\-]{0,11}$'),
 status text NOT NULL DEFAULT 'received' CHECK(status IN
  ('received','limited','sending','answered','queued','running','done','failed','uncertain','interrupted')),
 received_at timestamptz NOT NULL,
 message_id bigint,
 result_id uuid,
 error text CHECK(error IS NULL OR length(error)<=300),
 started_at timestamptz,
 finished_at timestamptz,
 delivered_at timestamptz
);
CREATE INDEX telegram_commands_recent ON telegram_commands(owner_id,received_at DESC);
CREATE INDEX telegram_commands_open ON telegram_commands(status,received_at) WHERE status IN ('queued','running');
ALTER TABLE telegram_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_commands FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON telegram_commands
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT,UPDATE ON telegram_commands TO thesis_app;
