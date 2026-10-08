CREATE TABLE idea_proposals (
 id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES accounts(id), instrument_id uuid NOT NULL REFERENCES instruments(id),
 base_version_id uuid, snapshot_id bigint NOT NULL REFERENCES research_snapshots(id), call_id uuid NOT NULL REFERENCES model_calls(id),
 request_key text NOT NULL, ordinal integer NOT NULL CHECK(ordinal BETWEEN 0 AND 2),
 kind text NOT NULL CHECK(kind IN ('reasoning','numeric','event')),
 operation text NOT NULL CHECK(operation IN ('add','update','remove')),
 target_condition_id uuid, proposed jsonb NOT NULL, rationale text NOT NULL, citations jsonb NOT NULL, packet jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id,id), UNIQUE(owner_id,request_key,ordinal),
 FOREIGN KEY(owner_id,base_version_id) REFERENCES thesis_versions(owner_id,id),
 CHECK((kind='reasoning' AND target_condition_id IS NULL AND operation='update') OR
       (kind<>'reasoning' AND ((operation='add' AND target_condition_id IS NULL) OR (operation IN ('update','remove') AND target_condition_id IS NOT NULL))))
);
CREATE TABLE proposal_decisions (
 owner_id uuid NOT NULL,proposal_id uuid NOT NULL,action text NOT NULL CHECK(action IN ('approved','rejected')),
 accepted_version_id uuid,request_hash text NOT NULL,approved_definition jsonb,created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(owner_id,proposal_id),
 FOREIGN KEY(owner_id,proposal_id) REFERENCES idea_proposals(owner_id,id),
 FOREIGN KEY(owner_id,accepted_version_id) REFERENCES thesis_versions(owner_id,id),
 CHECK((action='approved' AND accepted_version_id IS NOT NULL AND approved_definition IS NOT NULL) OR
       (action='rejected' AND accepted_version_id IS NULL AND approved_definition IS NULL))
);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['idea_proposals','proposal_decisions'] LOOP
 EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY account_scope ON %I USING(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
 EXECUTE format('GRANT SELECT,INSERT ON %I TO thesis_app',t);
 EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION immutable_record()',t);
 END LOOP;
END $$;
CREATE FUNCTION proposal_target_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.base_version_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM thesis_versions v JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id
  WHERE v.id=NEW.base_version_id AND v.owner_id=NEW.owner_id AND t.instrument_id=NEW.instrument_id
 ) THEN RAISE EXCEPTION 'Proposal base does not match owner and company'; END IF;
 IF NOT EXISTS(SELECT 1 FROM research_snapshots WHERE id=NEW.snapshot_id AND instrument_id=NEW.instrument_id) THEN
  RAISE EXCEPTION 'Proposal snapshot does not match company'; END IF;
 IF NEW.target_condition_id IS NOT NULL THEN
  IF NEW.kind='numeric' AND NOT EXISTS(SELECT 1 FROM version_conditions WHERE owner_id=NEW.owner_id AND version_id=NEW.base_version_id AND condition_id=NEW.target_condition_id) THEN
   RAISE EXCEPTION 'Proposal target is not in this numeric revision';
  ELSIF NEW.kind='event' AND NOT EXISTS(SELECT 1 FROM version_events WHERE owner_id=NEW.owner_id AND version_id=NEW.base_version_id AND condition_id=NEW.target_condition_id) THEN
   RAISE EXCEPTION 'Proposal target is not in this event revision';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_proposal_target BEFORE INSERT ON idea_proposals FOR EACH ROW EXECUTE FUNCTION proposal_target_membership();
