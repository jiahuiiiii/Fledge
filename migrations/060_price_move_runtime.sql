CREATE TABLE move_watch_state (
 owner_id uuid PRIMARY KEY REFERENCES accounts,
 next_check_at timestamptz NOT NULL,
 claim_token uuid,lease_until timestamptz,last_check_at timestamptz,error text
);
CREATE TABLE move_watch_runs (
 id uuid PRIMARY KEY,owner_id uuid NOT NULL REFERENCES accounts,
 started_at timestamptz NOT NULL,completed_at timestamptz NOT NULL,
 status text NOT NULL CHECK(status IN ('completed','failed','stopped')),
 checked_companies integer NOT NULL CHECK(checked_companies>=0),
 events_created integer NOT NULL CHECK(events_created>=0),error text,
 CHECK(completed_at>=started_at)
);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['move_watch_state','move_watch_runs'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('CREATE POLICY account_scope ON %I USING(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
  EXECUTE format('GRANT SELECT,INSERT ON %I TO thesis_app',t);
 END LOOP;
END $$;
GRANT UPDATE ON move_watch_state TO thesis_app;
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON move_watch_runs FOR EACH ROW EXECUTE FUNCTION immutable_record();

ALTER TABLE telegram_deliveries DROP CONSTRAINT telegram_deliveries_kind_check;
ALTER TABLE telegram_deliveries ADD CHECK(kind IN ('company','idea','condition','test','move'));
CREATE OR REPLACE FUNCTION telegram_membership() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE valid boolean:=false;
BEGIN
 IF TG_OP='UPDATE' THEN
  IF (NEW.id,NEW.owner_id,NEW.kind,NEW.event_id,NEW.event_at,NEW.created_at)
     IS DISTINCT FROM (OLD.id,OLD.owner_id,OLD.kind,OLD.event_id,OLD.event_at,OLD.created_at)
  THEN RAISE EXCEPTION 'Telegram delivery identity is immutable'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.kind='test' THEN valid:=true;
 ELSIF NEW.kind='company' THEN
  SELECT EXISTS(SELECT 1 FROM research_alerts WHERE owner_id=NEW.owner_id AND id=NEW.event_id AND created_at=NEW.event_at) INTO valid;
 ELSIF NEW.kind='idea' THEN
  SELECT EXISTS(SELECT 1 FROM idea_alert_publications WHERE owner_id=NEW.owner_id AND check_id=NEW.event_id AND created_at=NEW.event_at) INTO valid;
 ELSIF NEW.kind='condition' THEN
  SELECT EXISTS(SELECT 1 FROM change_events WHERE owner_id=NEW.owner_id AND id=NEW.event_id AND created_at=NEW.event_at) INTO valid;
 ELSIF NEW.kind='move' THEN
  SELECT EXISTS(SELECT 1 FROM move_events WHERE owner_id=NEW.owner_id AND id=NEW.event_id AND created_at=NEW.event_at AND NOT preview) INTO valid;
 END IF;
 IF NOT valid THEN RAISE EXCEPTION 'Telegram delivery is outside its owner or publication'; END IF;
 RETURN NEW;
END $$;
