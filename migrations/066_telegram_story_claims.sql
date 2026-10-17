-- Only send-intent metadata. No message text, destination or account enrollment.
CREATE TABLE telegram_story_claims (
 owner_id uuid NOT NULL,delivery_id uuid NOT NULL,
 attempt integer NOT NULL CHECK(attempt BETWEEN 1 AND 3),
 story_key text NOT NULL CHECK(story_key ~ '^[a-z_]+:[0-9a-f]{64}$'),
 created_at timestamptz NOT NULL,
 PRIMARY KEY(owner_id,delivery_id,attempt,story_key),
 FOREIGN KEY(owner_id,delivery_id) REFERENCES telegram_deliveries(owner_id,id)
);
CREATE INDEX telegram_story_lookup ON telegram_story_claims(owner_id,story_key);
ALTER TABLE telegram_story_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_story_claims FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON telegram_story_claims
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT ON telegram_story_claims TO thesis_app;
CREATE FUNCTION telegram_story_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM telegram_deliveries t WHERE t.owner_id=NEW.owner_id
  AND t.id=NEW.delivery_id AND t.attempts=NEW.attempt AND t.status='sending'
  AND t.kind IN ('company','idea','condition','move','digest') AND t.attempted_at=NEW.created_at
  AND (t.kind<>'company' OR EXISTS(SELECT 1 FROM research_alerts a WHERE a.owner_id=t.owner_id AND a.id=t.event_id AND NOT a.preview))
  AND (t.kind<>'move' OR EXISTS(SELECT 1 FROM move_events a WHERE a.owner_id=t.owner_id AND a.id=t.event_id AND NOT a.preview)))
 THEN RAISE EXCEPTION 'Story claims must belong to this actual send attempt'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_membership BEFORE INSERT ON telegram_story_claims
 FOR EACH ROW EXECUTE FUNCTION telegram_story_membership();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON telegram_story_claims
 FOR EACH ROW EXECUTE FUNCTION immutable_record();
