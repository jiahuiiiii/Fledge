CREATE TABLE version_events (
 owner_id uuid NOT NULL,version_id uuid NOT NULL,condition_id uuid NOT NULL,
 description text NOT NULL CHECK(length(btrim(description)) BETWEEN 5 AND 400),
 evidence_requirement text NOT NULL CHECK(length(btrim(evidence_requirement)) BETWEEN 5 AND 600),
 role text NOT NULL CHECK(role IN ('required','risk')),
 window_start date NOT NULL,deadline date NOT NULL CHECK(deadline>=window_start),
 PRIMARY KEY(owner_id,version_id,condition_id),
 FOREIGN KEY(owner_id,version_id) REFERENCES thesis_versions(owner_id,id)
);
CREATE TRIGGER sealed_membership BEFORE INSERT ON version_events FOR EACH ROW EXECUTE FUNCTION condition_belongs_to_open_revision();
CREATE TABLE event_evidence_reviews (
 id uuid PRIMARY KEY,owner_id uuid NOT NULL,version_id uuid NOT NULL,
 snapshot_id bigint NOT NULL REFERENCES research_snapshots(id),call_id uuid NOT NULL REFERENCES model_calls(id),
 request_key text NOT NULL,packet jsonb NOT NULL,result jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(owner_id,version_id) REFERENCES thesis_versions(owner_id,id),
 UNIQUE(owner_id,request_key),UNIQUE(owner_id,id,version_id)
);
CREATE TABLE event_results (
 owner_id uuid NOT NULL,evaluation_id uuid NOT NULL,version_id uuid NOT NULL,condition_id uuid NOT NULL,
 outcome text NOT NULL CHECK(outcome IN ('met','not_met','unknown')),
 state text NOT NULL CHECK(state IN ('confirmed','risk_reported','denied_report','uncertain','not_checked','deadline_unconfirmed','not_started','conflicting')),
 review_id uuid,explanation text NOT NULL,citations jsonb NOT NULL DEFAULT '[]',
 PRIMARY KEY(evaluation_id,condition_id),
 FOREIGN KEY(owner_id,evaluation_id,version_id) REFERENCES evaluations(owner_id,id,version_id),
 FOREIGN KEY(owner_id,version_id,condition_id) REFERENCES version_events(owner_id,version_id,condition_id),
 FOREIGN KEY(owner_id,review_id,version_id) REFERENCES event_evidence_reviews(owner_id,id,version_id)
);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['version_events','event_evidence_reviews','event_results'] LOOP
 EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY account_scope ON %I USING(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
 EXECUTE format('GRANT SELECT,INSERT ON %I TO thesis_app',t);
 EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION immutable_record()',t);
 END LOOP;
END $$;
CREATE OR REPLACE FUNCTION complete_evaluation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected integer;actual integer;events_expected integer;events_actual integer;
BEGIN
 SELECT count(*) INTO expected FROM version_conditions WHERE owner_id=NEW.owner_id AND version_id=NEW.version_id;
 SELECT count(*) INTO actual FROM condition_results WHERE owner_id=NEW.owner_id AND evaluation_id=NEW.id;
 SELECT count(*) INTO events_expected FROM version_events WHERE owner_id=NEW.owner_id AND version_id=NEW.version_id;
 SELECT count(*) INTO events_actual FROM event_results WHERE owner_id=NEW.owner_id AND evaluation_id=NEW.id;
 IF expected+events_expected=0 OR expected<>actual OR events_expected<>events_actual THEN RAISE EXCEPTION 'Evaluation must contain every condition result'; END IF;
 RETURN NEW;
END $$;
ALTER TABLE change_events DROP CONSTRAINT IF EXISTS change_events_kind_check;
ALTER TABLE change_events ADD CHECK(kind IN ('figures','coverage','evidence','expiry','event'));
