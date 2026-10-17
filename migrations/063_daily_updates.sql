-- Frozen daily membership and aggregate spending observations; no enrollment.
ALTER TABLE alert_routing_decisions ADD UNIQUE(owner_id,id);
CREATE TABLE daily_digests (
 id uuid PRIMARY KEY,owner_id uuid NOT NULL REFERENCES accounts,
 window_start timestamptz NOT NULL,window_end timestamptz NOT NULL,
 created_at timestamptz NOT NULL,policy text NOT NULL,preview boolean NOT NULL,
 UNIQUE(owner_id,id),UNIQUE(owner_id,window_end,policy),
 CHECK(window_end>window_start AND created_at>=window_end)
);
CREATE TABLE daily_digest_members (
 owner_id uuid NOT NULL,digest_id uuid NOT NULL,position integer NOT NULL CHECK(position>=0),
 route_id uuid NOT NULL,kind text NOT NULL CHECK(kind IN ('company','idea','condition','move')),
 event_id uuid NOT NULL,PRIMARY KEY(owner_id,digest_id,position),UNIQUE(owner_id,route_id),UNIQUE(owner_id,kind,event_id),
 FOREIGN KEY(owner_id,digest_id) REFERENCES daily_digests(owner_id,id),
 FOREIGN KEY(owner_id,route_id) REFERENCES alert_routing_decisions(owner_id,id)
);
CREATE FUNCTION daily_digest_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM alert_routing_decisions r JOIN daily_digests d
  ON d.owner_id=r.owner_id AND d.id=NEW.digest_id
  WHERE r.owner_id=NEW.owner_id AND r.id=NEW.route_id AND r.kind=NEW.kind
  AND r.event_id=NEW.event_id AND r.channel='digest'
  AND r.created_at>=d.window_start AND r.created_at<d.window_end)
 THEN RAISE EXCEPTION 'Daily membership must name a medium route in its private window'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_membership BEFORE INSERT ON daily_digest_members
 FOR EACH ROW EXECUTE FUNCTION daily_digest_membership();

CREATE TABLE daily_spend_reports (
 id uuid PRIMARY KEY,owner_id uuid NOT NULL REFERENCES accounts,day date NOT NULL,
 window_start timestamptz NOT NULL,window_end timestamptz NOT NULL,observed_at timestamptz NOT NULL,
 policy text NOT NULL,charged_nano_usd bigint NOT NULL CHECK(charged_nano_usd>=0),
 pending_max_nano_usd bigint NOT NULL CHECK(pending_max_nano_usd>=0),
 settled_calls integer NOT NULL CHECK(settled_calls>=0),pending_calls integer NOT NULL CHECK(pending_calls>=0),
 experiment_charged_nano_usd bigint NOT NULL CHECK(experiment_charged_nano_usd>=0),
 UNIQUE(owner_id,id),UNIQUE(owner_id,day,policy),
 CHECK(window_end>window_start AND observed_at>=window_end AND experiment_charged_nano_usd<=charged_nano_usd)
);
CREATE TABLE daily_cost_notices (
 id uuid PRIMARY KEY,owner_id uuid NOT NULL REFERENCES accounts,day date NOT NULL,
 threshold_nano_usd bigint NOT NULL CHECK(threshold_nano_usd>0),
 charged_nano_usd bigint NOT NULL,pending_max_nano_usd bigint NOT NULL CHECK(pending_max_nano_usd>=0),
 created_at timestamptz NOT NULL,policy text NOT NULL,preview boolean NOT NULL,
 UNIQUE(owner_id,id),UNIQUE(owner_id,day,policy),CHECK(charged_nano_usd>threshold_nano_usd)
);
CREATE TABLE daily_updates_state (
 owner_id uuid PRIMARY KEY REFERENCES accounts,next_check_at timestamptz NOT NULL,
 last_attempt_at timestamptz,last_success_at timestamptz,error text CHECK(error IN ('preparation_failed','too_many_records'))
);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['daily_digests','daily_digest_members','daily_spend_reports','daily_cost_notices','daily_updates_state'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('CREATE POLICY account_scope ON %I USING(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
  EXECUTE format('GRANT SELECT,INSERT ON %I TO thesis_app',t);
  IF t<>'daily_updates_state' THEN
   EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION immutable_record()',t);
  END IF;
 END LOOP;
END $$;
GRANT UPDATE ON daily_updates_state TO thesis_app;
CREATE INDEX daily_digest_recent ON daily_digests(owner_id,window_end DESC,id);
