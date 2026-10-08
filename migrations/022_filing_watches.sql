-- Private scheduling around the existing shared SEC collector. No watches enrolled.
CREATE TABLE filing_watches (
 owner_id uuid NOT NULL REFERENCES accounts,
 instrument_id uuid NOT NULL REFERENCES sec_companies(instrument_id),
 enabled boolean NOT NULL DEFAULT false,
 next_check_at timestamptz, claim_token uuid, lease_until timestamptz,
 PRIMARY KEY(owner_id,instrument_id),
 CHECK(enabled=(next_check_at IS NOT NULL)),
 CHECK((claim_token IS NULL)=(lease_until IS NULL))
);
CREATE TABLE filing_watch_checks (
 id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES accounts,
 instrument_id uuid NOT NULL REFERENCES sec_companies(instrument_id),
 scheduled_at timestamptz NOT NULL, started_at timestamptz NOT NULL,
 lease_until timestamptz NOT NULL CHECK(lease_until>started_at),
 UNIQUE(owner_id,id)
);
CREATE TABLE filing_watch_results (
 check_id uuid PRIMARY KEY, owner_id uuid NOT NULL,
 completed_at timestamptz NOT NULL,
 outcome text NOT NULL CHECK(outcome IN ('changed','unchanged','recent','failed','interrupted')),
 source_check_id uuid REFERENCES source_checks,
 message text NOT NULL,
 FOREIGN KEY(owner_id,check_id) REFERENCES filing_watch_checks(owner_id,id),
 CHECK((outcome IN ('changed','unchanged'))=(source_check_id IS NOT NULL))
);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['filing_watches','filing_watch_checks','filing_watch_results'] LOOP
 EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY account_scope ON %I USING(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
 EXECUTE format('GRANT SELECT,INSERT ON %I TO thesis_app',t);
 END LOOP;
 FOREACH t IN ARRAY ARRAY['filing_watch_checks','filing_watch_results'] LOOP
 EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION immutable_record()',t);
 END LOOP;
END $$;
GRANT UPDATE ON filing_watches TO thesis_app;
CREATE INDEX filing_watch_history ON filing_watch_checks(owner_id,instrument_id,started_at DESC,id DESC);
CREATE FUNCTION filing_watch_result_membership() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE started filing_watch_checks; BEGIN
 SELECT * INTO started FROM filing_watch_checks WHERE owner_id=NEW.owner_id AND id=NEW.check_id;
 IF NEW.completed_at<started.started_at THEN RAISE EXCEPTION 'Completion precedes start'; END IF;
 IF NEW.outcome<>'interrupted' AND NEW.completed_at>=started.lease_until THEN RAISE EXCEPTION 'Completion lease expired'; END IF;
 IF NEW.source_check_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM source_checks WHERE id=NEW.source_check_id AND instrument_id=started.instrument_id AND source_id='sec-companyfacts' AND outcome='success' AND checked_at>=started.started_at AND checked_at<=NEW.completed_at) THEN RAISE EXCEPTION 'Wrong source check'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_membership BEFORE INSERT ON filing_watch_results FOR EACH ROW EXECUTE FUNCTION filing_watch_result_membership();
