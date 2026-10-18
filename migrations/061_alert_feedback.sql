-- Explicit alert feedback only; no backfill or enrollment.
CREATE FUNCTION alert_event_exists(account uuid, event_kind text, event uuid)
RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT CASE event_kind
 WHEN 'company' THEN EXISTS(SELECT 1 FROM research_alerts WHERE owner_id=account AND id=event)
 WHEN 'idea' THEN EXISTS(SELECT 1 FROM idea_alert_publications WHERE owner_id=account AND check_id=event)
 WHEN 'condition' THEN EXISTS(SELECT 1 FROM change_events WHERE owner_id=account AND id=event)
 WHEN 'move' THEN EXISTS(SELECT 1 FROM move_events WHERE owner_id=account AND id=event)
 ELSE false END
$$;
CREATE TABLE alert_feedback (
 id uuid PRIMARY KEY,owner_id uuid NOT NULL REFERENCES accounts,
 kind text NOT NULL CHECK(kind IN ('company','idea','condition','move')),
 event_id uuid NOT NULL,value text NOT NULL CHECK(value IN ('useful','not_useful')),
 source text NOT NULL CHECK(source IN ('app','telegram')),
 created_at timestamptz NOT NULL,request_key text,
 UNIQUE(owner_id,request_key)
);
CREATE INDEX alert_feedback_latest ON alert_feedback(owner_id,kind,event_id,created_at DESC,id DESC);
ALTER TABLE alert_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_feedback FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON alert_feedback
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT ON alert_feedback TO thesis_app;
CREATE FUNCTION alert_feedback_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT alert_event_exists(NEW.owner_id,NEW.kind,NEW.event_id)
 THEN RAISE EXCEPTION 'Alert feedback is outside its owner or publication'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_membership BEFORE INSERT ON alert_feedback
 FOR EACH ROW EXECUTE FUNCTION alert_feedback_membership();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON alert_feedback
 FOR EACH ROW EXECUTE FUNCTION immutable_record();

-- A bot has one Telegram update cursor. App accounts must not acknowledge
-- one another's connection or rating updates independently. Host-service only;
-- no raw message text or Telegram identity is retained in this global table.
CREATE TABLE telegram_poll_state (
 bot_fingerprint text PRIMARY KEY CHECK(length(bot_fingerprint)=64),
 update_offset bigint NOT NULL DEFAULT 0 CHECK(update_offset>=0),
 next_poll_at timestamptz,last_update_at timestamptz
);
