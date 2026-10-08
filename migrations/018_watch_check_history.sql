CREATE TABLE watch_checks (
 id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES accounts,
 instrument_id uuid NOT NULL REFERENCES instruments,
 started_at timestamptz NOT NULL, lease_until timestamptz NOT NULL,
 interval_minutes integer NOT NULL CHECK(interval_minutes IN (60,240)),
 match_idea boolean NOT NULL, baseline_id uuid,
 version_id uuid,
 UNIQUE(owner_id,id),
 FOREIGN KEY(instrument_id,baseline_id) REFERENCES sentiment_analyses(instrument_id,id),
 FOREIGN KEY(owner_id,version_id) REFERENCES thesis_versions(owner_id,id)
);
CREATE TABLE watch_check_results (
 owner_id uuid NOT NULL, check_id uuid PRIMARY KEY,
 completed_at timestamptz NOT NULL,
 status text NOT NULL CHECK(status IN ('completed','failed','stopped')),
 analysis_id uuid, idea_check_id uuid,
 details jsonb NOT NULL,
 FOREIGN KEY(owner_id,check_id) REFERENCES watch_checks(owner_id,id),
 FOREIGN KEY(owner_id,idea_check_id) REFERENCES idea_alert_checks(owner_id,id),
 FOREIGN KEY(analysis_id) REFERENCES sentiment_analyses(id)
);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['watch_checks','watch_check_results'] LOOP
 EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY account_scope ON %I USING(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
 EXECUTE format('GRANT SELECT,INSERT ON %I TO thesis_app',t);
 EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION immutable_record()',t);
 END LOOP;
END $$;
CREATE INDEX watch_checks_history ON watch_checks(owner_id,instrument_id,started_at DESC,id DESC);
CREATE FUNCTION watch_check_membership() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE started watch_checks; BEGIN
 SELECT * INTO started FROM watch_checks WHERE id=NEW.check_id AND owner_id=NEW.owner_id;
 IF NEW.completed_at<started.started_at THEN RAISE EXCEPTION 'Completion precedes start'; END IF;
 IF NEW.analysis_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM sentiment_analyses WHERE id=NEW.analysis_id AND instrument_id=started.instrument_id) THEN RAISE EXCEPTION 'Wrong company analysis'; END IF;
 IF NEW.idea_check_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM idea_alert_checks WHERE id=NEW.idea_check_id AND owner_id=NEW.owner_id AND instrument_id=started.instrument_id AND analysis_id=NEW.analysis_id) THEN RAISE EXCEPTION 'Wrong private check'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_membership BEFORE INSERT ON watch_check_results FOR EACH ROW EXECUTE FUNCTION watch_check_membership();
CREATE FUNCTION watch_start_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM thesis_versions v JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id WHERE v.id=NEW.version_id AND v.owner_id=NEW.owner_id AND t.instrument_id=NEW.instrument_id) THEN RAISE EXCEPTION 'Saved reasoning belongs to another company'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_membership BEFORE INSERT ON watch_checks FOR EACH ROW EXECUTE FUNCTION watch_start_membership();
