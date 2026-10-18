-- Delivery preparation only; no settings, saved previews or research are changed.
ALTER TABLE alert_routing_decisions DROP CONSTRAINT alert_routing_decisions_preview_check;
CREATE FUNCTION alert_routing_mode() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT NEW.preview AND (
  (NEW.kind='company' AND EXISTS(SELECT 1 FROM research_alerts WHERE owner_id=NEW.owner_id AND id=NEW.event_id AND preview)) OR
  (NEW.kind='move' AND EXISTS(SELECT 1 FROM move_events WHERE owner_id=NEW.owner_id AND id=NEW.event_id AND preview)))
 THEN RAISE EXCEPTION 'A preview publication cannot acquire a live route'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_mode BEFORE INSERT ON alert_routing_decisions
 FOR EACH ROW EXECUTE FUNCTION alert_routing_mode();
-- A real recap must never include a shadow route. Existing previews stay valid.
CREATE OR REPLACE FUNCTION daily_digest_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM alert_routing_decisions r JOIN daily_digests d
  ON d.owner_id=r.owner_id AND d.id=NEW.digest_id
  WHERE r.owner_id=NEW.owner_id AND r.id=NEW.route_id AND r.kind=NEW.kind
  AND r.event_id=NEW.event_id AND r.channel='digest' AND (d.preview OR NOT r.preview)
  AND r.created_at>=d.window_start AND r.created_at<d.window_end)
 THEN RAISE EXCEPTION 'Daily membership must name a medium route in its private window and mode'; END IF;
 RETURN NEW;
END $$;

ALTER TABLE telegram_deliveries DROP CONSTRAINT telegram_deliveries_kind_check;
ALTER TABLE telegram_deliveries ADD CHECK(kind IN ('company','idea','condition','test','move','digest','cost'));
ALTER TABLE telegram_deliveries ADD UNIQUE(owner_id,id);
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
 ELSIF NEW.kind='digest' THEN
  SELECT EXISTS(SELECT 1 FROM daily_digests d WHERE d.owner_id=NEW.owner_id AND d.id=NEW.event_id
   AND d.created_at=NEW.event_at AND NOT d.preview
   AND EXISTS(SELECT 1 FROM daily_digest_members m WHERE m.owner_id=d.owner_id AND m.digest_id=d.id)
   AND NOT EXISTS(SELECT 1 FROM daily_digest_members m JOIN alert_routing_decisions r ON r.owner_id=m.owner_id AND r.id=m.route_id
    WHERE m.owner_id=d.owner_id AND m.digest_id=d.id AND r.preview)) INTO valid;
 ELSIF NEW.kind='cost' THEN
  SELECT EXISTS(SELECT 1 FROM daily_cost_notices WHERE owner_id=NEW.owner_id AND id=NEW.event_id AND created_at=NEW.event_at AND NOT preview) INTO valid;
 END IF;
 IF NOT valid THEN RAISE EXCEPTION 'Telegram delivery is outside its owner or publication'; END IF;
 RETURN NEW;
END $$;

-- Which original alert each numbered button actually represented on each send.
-- A rejected/rate-limited attempt can be rendered again with different access;
-- only the confirmed message's attempt is used when accepting a rating.
CREATE TABLE telegram_digest_items (
 owner_id uuid NOT NULL,delivery_id uuid NOT NULL,
 attempt integer NOT NULL CHECK(attempt BETWEEN 1 AND 3),
 position integer NOT NULL CHECK(position BETWEEN 0 AND 4),member_position integer NOT NULL CHECK(member_position>=0),
 PRIMARY KEY(owner_id,delivery_id,attempt,position),UNIQUE(owner_id,delivery_id,attempt,member_position),
 FOREIGN KEY(owner_id,delivery_id) REFERENCES telegram_deliveries(owner_id,id)
);
ALTER TABLE telegram_digest_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_digest_items FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON telegram_digest_items
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT ON telegram_digest_items TO thesis_app;
CREATE FUNCTION telegram_digest_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM telegram_deliveries t JOIN daily_digest_members m
  ON m.owner_id=t.owner_id AND m.digest_id=t.event_id
  WHERE t.owner_id=NEW.owner_id AND t.id=NEW.delivery_id AND t.kind='digest'
  AND t.status='sending' AND t.attempts=NEW.attempt AND m.position=NEW.member_position)
 THEN RAISE EXCEPTION 'Digest rating button must name an actual member of this send attempt'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_membership BEFORE INSERT ON telegram_digest_items
 FOR EACH ROW EXECUTE FUNCTION telegram_digest_membership();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON telegram_digest_items
 FOR EACH ROW EXECUTE FUNCTION immutable_record();
