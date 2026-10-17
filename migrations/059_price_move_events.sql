-- Immutable private move previews, distinct from text-only company alerts.
CREATE TABLE move_events (
 id uuid PRIMARY KEY,owner_id uuid NOT NULL REFERENCES accounts,
 instrument_id uuid NOT NULL REFERENCES instruments,
 created_at timestamptz NOT NULL,session_date date NOT NULL,
 event_type text NOT NULL CHECK(event_type IN ('company','market')),
 direction text NOT NULL CHECK(direction IN ('up','down','flat')),
 preview boolean NOT NULL DEFAULT true,
 policy text NOT NULL,payload jsonb NOT NULL,headlines jsonb NOT NULL,
 UNIQUE(owner_id,id)
);
CREATE INDEX move_events_latest ON move_events(owner_id,created_at DESC,id DESC);
CREATE TABLE move_event_members (
 owner_id uuid NOT NULL,event_id uuid NOT NULL,instrument_id uuid NOT NULL REFERENCES instruments,
 quote_id uuid NOT NULL REFERENCES market_quotes,
 qqq_id uuid REFERENCES reference_price_snapshots,spy_id uuid REFERENCES reference_price_snapshots,
 sector_id uuid REFERENCES reference_price_snapshots,history_id uuid REFERENCES price_history_snapshots,
 triggered boolean NOT NULL,payload jsonb NOT NULL,
 PRIMARY KEY(owner_id,event_id,instrument_id),
 FOREIGN KEY(owner_id,event_id) REFERENCES move_events(owner_id,id)
);
CREATE TABLE move_trigger_claims (
 owner_id uuid NOT NULL,instrument_id uuid NOT NULL,
 session_date date NOT NULL,direction text NOT NULL CHECK(direction IN ('up','down','flat')),
 event_id uuid NOT NULL,
 PRIMARY KEY(owner_id,instrument_id,session_date,direction),
 FOREIGN KEY(owner_id,event_id,instrument_id) REFERENCES move_event_members(owner_id,event_id,instrument_id)
);
CREATE TABLE move_explainer_attempts (
 owner_id uuid NOT NULL,event_id uuid NOT NULL,request_key text NOT NULL UNIQUE,
 created_at timestamptz NOT NULL,
 PRIMARY KEY(owner_id,event_id),FOREIGN KEY(owner_id,event_id) REFERENCES move_events(owner_id,id)
);
CREATE TABLE move_explanations (
 owner_id uuid NOT NULL,event_id uuid NOT NULL,call_id uuid REFERENCES model_calls,
 created_at timestamptz NOT NULL,status text NOT NULL CHECK(status IN ('valid','no_clear','failed')),
 result jsonb NOT NULL,
 PRIMARY KEY(owner_id,event_id),FOREIGN KEY(owner_id,event_id) REFERENCES move_explainer_attempts(owner_id,event_id)
);
CREATE TABLE move_event_reviews (
 owner_id uuid NOT NULL,event_id uuid NOT NULL,
 action text NOT NULL CHECK(action IN ('reviewed','unresolved')),
 created_at timestamptz NOT NULL,
 PRIMARY KEY(owner_id,event_id),FOREIGN KEY(owner_id,event_id) REFERENCES move_events(owner_id,id)
);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['move_events','move_event_members','move_trigger_claims','move_explainer_attempts','move_explanations','move_event_reviews'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('CREATE POLICY account_scope ON %I USING(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
  EXECUTE format('GRANT SELECT,INSERT ON %I TO thesis_app',t);
  EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION immutable_record()',t);
 END LOOP;
END $$;
CREATE FUNCTION move_member_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM market_quotes q JOIN instruments i ON i.id=q.instrument_id
   WHERE q.id=NEW.quote_id AND q.instrument_id=NEW.instrument_id AND i.symbol=NEW.payload->>'symbol')
 THEN RAISE EXCEPTION 'Move quote belongs to another company'; END IF;
 IF NEW.qqq_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM reference_price_snapshots WHERE id=NEW.qqq_id AND symbol='QQQ' AND resource='quote')
 THEN RAISE EXCEPTION 'Wrong Nasdaq reference'; END IF;
 IF NEW.spy_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM reference_price_snapshots WHERE id=NEW.spy_id AND symbol='SPY' AND resource='quote')
 THEN RAISE EXCEPTION 'Wrong broad-market reference'; END IF;
 IF NEW.sector_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM reference_price_snapshots p JOIN reference_instruments r USING(symbol)
   WHERE p.id=NEW.sector_id AND p.resource='quote' AND r.role='sector')
 THEN RAISE EXCEPTION 'Wrong sector reference'; END IF;
 IF NEW.history_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM price_history_snapshots WHERE id=NEW.history_id AND instrument_id=NEW.instrument_id)
 THEN RAISE EXCEPTION 'Daily history belongs to another company'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_membership BEFORE INSERT ON move_event_members FOR EACH ROW EXECUTE FUNCTION move_member_membership();
CREATE FUNCTION move_claim_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM move_events e JOIN move_event_members m ON m.owner_id=e.owner_id AND m.event_id=e.id
  WHERE e.owner_id=NEW.owner_id AND e.id=NEW.event_id AND e.session_date=NEW.session_date AND e.direction=NEW.direction
  AND m.instrument_id=NEW.instrument_id AND m.triggered)
 THEN RAISE EXCEPTION 'A move claim needs a qualifying event member'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_membership BEFORE INSERT ON move_trigger_claims FOR EACH ROW EXECUTE FUNCTION move_claim_membership();
CREATE FUNCTION move_explanation_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.call_id IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM model_calls c JOIN move_explainer_attempts a ON a.request_key=c.request_key AND a.owner_id=c.owner_id
  WHERE c.id=NEW.call_id AND a.owner_id=NEW.owner_id AND a.event_id=NEW.event_id)
 THEN RAISE EXCEPTION 'Move explanation belongs to another attempt'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_membership BEFORE INSERT ON move_explanations FOR EACH ROW EXECUTE FUNCTION move_explanation_membership();
