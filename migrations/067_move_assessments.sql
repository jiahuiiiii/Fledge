-- Retain assessments before publication, including non-triggers and omissions.
-- run_id deliberately has no result FK: evidence survives an interrupted worker
-- which never reaches move_watch_runs. The active lease authenticates insertion.
CREATE TABLE move_assessments (
 id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES accounts,
 run_id uuid NOT NULL, instrument_id uuid NOT NULL REFERENCES instruments,
 observed_at timestamptz NOT NULL, quote_id uuid REFERENCES market_quotes,
 status text NOT NULL CHECK(status IN ('measured','no_quote','invalid_quote','references_withheld')),
 qualifies boolean NOT NULL, already_claimed boolean NOT NULL,
 preview boolean NOT NULL, policy text NOT NULL, payload jsonb NOT NULL,
 UNIQUE(owner_id,run_id,instrument_id),
 CHECK(payload ?& ARRAY['thresholds','measure']),
 CHECK(jsonb_typeof(payload->'thresholds')='object'),
 CHECK((jsonb_typeof(payload->'measure')='object')=(status='measured')),
 CHECK(NOT qualifies OR status='measured'),
 CHECK(NOT already_claimed OR status='measured'),
 CHECK((quote_id IS NULL)=(status IN ('no_quote','references_withheld')))
);
CREATE INDEX move_assessments_window ON move_assessments(owner_id,observed_at,instrument_id);
ALTER TABLE move_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE move_assessments FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON move_assessments
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT ON move_assessments TO thesis_app;
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON move_assessments
 FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE FUNCTION move_assessment_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM move_watch_state s JOIN news_watches w USING(owner_id)
   WHERE s.owner_id=NEW.owner_id AND s.claim_token=NEW.run_id AND s.lease_until>NEW.observed_at
   AND w.instrument_id=NEW.instrument_id AND w.enabled)
 THEN RAISE EXCEPTION 'A move assessment needs its active worker and watched company'; END IF;
 IF NEW.quote_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM market_quotes q
   WHERE q.id=NEW.quote_id AND q.instrument_id=NEW.instrument_id AND q.retrieved_at<=NEW.observed_at)
 THEN RAISE EXCEPTION 'Assessment quote belongs to another company or future capture'; END IF;
 IF NEW.status='measured' AND (
   NEW.payload->'measure'->>'quote_id' IS DISTINCT FROM NEW.quote_id::text
   OR (NEW.payload->'measure'->>'triggered')::boolean IS DISTINCT FROM NEW.qualifies
   OR NEW.payload->'measure'->>'policy' IS DISTINCT FROM NEW.policy
   OR NEW.payload->'measure'->'thresholds' IS DISTINCT FROM NEW.payload->'thresholds'
   OR NOT EXISTS(SELECT 1 FROM instruments WHERE id=NEW.instrument_id AND symbol=NEW.payload->'measure'->>'symbol'))
 THEN RAISE EXCEPTION 'Assessment inputs do not match their measured record'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_membership BEFORE INSERT ON move_assessments
 FOR EACH ROW EXECUTE FUNCTION move_assessment_membership();
