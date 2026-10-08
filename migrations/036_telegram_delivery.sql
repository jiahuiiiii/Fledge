-- Explicitly connected private Telegram chats. No account is enrolled on upgrade.
CREATE TABLE telegram_settings (
 owner_id uuid PRIMARY KEY REFERENCES accounts,
 bot_fingerprint text, bot_username text,
 chat_id bigint CHECK(chat_id>0), chat_label text,
 enabled boolean NOT NULL DEFAULT false, enabled_at timestamptz,
 link_hash text, link_expires_at timestamptz, update_offset bigint NOT NULL DEFAULT 0,
 next_send_at timestamptz,
 CHECK(NOT enabled OR (chat_id IS NOT NULL AND enabled_at IS NOT NULL AND bot_fingerprint IS NOT NULL))
);
CREATE TABLE telegram_deliveries (
 id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES accounts,
 kind text NOT NULL CHECK(kind IN ('company','idea','condition','test')),
 event_id uuid NOT NULL, event_at timestamptz NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 status text NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','sending','sent','failed','uncertain','skipped','cancelled')),
 attempts integer NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 3),
 retry_at timestamptz, attempted_at timestamptz, sent_at timestamptz,
 message_id bigint, error text,
 UNIQUE(owner_id,kind,event_id),
 CHECK(status<>'sent' OR (message_id IS NOT NULL AND sent_at IS NOT NULL))
);
CREATE INDEX telegram_pending ON telegram_deliveries(owner_id,status,created_at);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['telegram_settings','telegram_deliveries'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('CREATE POLICY account_scope ON %I USING(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
  EXECUTE format('GRANT SELECT,INSERT,UPDATE ON %I TO thesis_app',t);
 END LOOP;
END $$;
-- Outbox identity must refer to an actual published alert owned by this account.
CREATE FUNCTION telegram_membership() RETURNS trigger LANGUAGE plpgsql AS $$
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
 END IF;
 IF NOT valid THEN RAISE EXCEPTION 'Telegram delivery is outside its owner or publication'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER validate_membership BEFORE INSERT OR UPDATE ON telegram_deliveries FOR EACH ROW EXECUTE FUNCTION telegram_membership();
