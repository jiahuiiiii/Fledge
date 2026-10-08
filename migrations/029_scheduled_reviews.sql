-- Optional local weekly reviews; no owner is enrolled by this migration.
CREATE TABLE review_schedules (
 owner_id uuid PRIMARY KEY REFERENCES accounts,
 enabled boolean NOT NULL DEFAULT false,
 revision integer NOT NULL CHECK(revision>0),
 weekday smallint NOT NULL CHECK(weekday BETWEEN 0 AND 6),
 minute_of_day smallint NOT NULL CHECK(minute_of_day BETWEEN 0 AND 1439),
 time_zone text NOT NULL CHECK(length(time_zone) BETWEEN 1 AND 80),
 next_due_at timestamptz,
 last_attempt_at timestamptz,
 retry_after timestamptz,
 error text CHECK(error IN ('too_many_records','generation_failed')),
 CHECK(enabled=(next_due_at IS NOT NULL))
);
CREATE TABLE scheduled_reviews (
 id uuid PRIMARY KEY,
 owner_id uuid NOT NULL REFERENCES accounts,
 schedule_revision integer NOT NULL CHECK(schedule_revision>0),
 scheduled_at timestamptz NOT NULL,
 generated_at timestamptz NOT NULL CHECK(generated_at>=scheduled_at),
 time_zone text NOT NULL,
 skipped_occurrences integer NOT NULL CHECK(skipped_occurrences>=0),
 manifest jsonb NOT NULL CHECK(jsonb_typeof(manifest)='object'),
 UNIQUE(owner_id,id),
 UNIQUE(owner_id,schedule_revision,scheduled_at)
);
CREATE TABLE scheduled_review_seen (
 owner_id uuid NOT NULL,
 review_id uuid NOT NULL,
 seen_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(owner_id,review_id),
 FOREIGN KEY(owner_id,review_id) REFERENCES scheduled_reviews(owner_id,id)
);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['review_schedules','scheduled_reviews','scheduled_review_seen'] LOOP
 EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY account_scope ON %I USING(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
 EXECUTE format('GRANT SELECT,INSERT ON %I TO thesis_app',t);
 END LOOP;
 FOREACH t IN ARRAY ARRAY['scheduled_reviews','scheduled_review_seen'] LOOP
 EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION immutable_record()',t);
 END LOOP;
END $$;
GRANT UPDATE ON review_schedules TO thesis_app;
CREATE INDEX scheduled_review_history ON scheduled_reviews(owner_id,scheduled_at DESC,id DESC);
CREATE FUNCTION scheduled_review_membership() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE e jsonb; valid boolean;
BEGIN
 IF jsonb_typeof(NEW.manifest->'records') IS DISTINCT FROM 'array'
 OR jsonb_array_length(NEW.manifest->'records')>1000
 OR (NEW.manifest->>'cutoff')::timestamptz IS DISTINCT FROM NEW.scheduled_at
 OR (NEW.manifest->>'generated_at')::timestamptz IS DISTINCT FROM NEW.generated_at
 OR (NEW.manifest->>'window_start') IS NULL
 OR (NEW.manifest->>'window_start')::timestamptz>=NEW.scheduled_at
 OR NEW.scheduled_at-(NEW.manifest->>'window_start')::timestamptz>interval '9 days'
 OR (SELECT count(DISTINCT (r->>'kind',r->>'id')) FROM jsonb_array_elements(NEW.manifest->'records') r)<>jsonb_array_length(NEW.manifest->'records')
 OR (NEW.manifest->>'total')::int IS DISTINCT FROM jsonb_array_length(NEW.manifest->'records')
 THEN RAISE EXCEPTION 'Invalid saved review manifest'; END IF;
 FOR e IN SELECT * FROM jsonb_array_elements(NEW.manifest->'records') LOOP
  valid:=false;
  IF e->>'kind'='idea' THEN
   SELECT EXISTS(SELECT 1 FROM idea_alert_checks a JOIN idea_alert_publications p ON p.check_id=a.id AND p.owner_id=a.owner_id WHERE a.owner_id=NEW.owner_id AND a.id=(e->>'id')::uuid AND a.instrument_id=(e->>'instrument_id')::uuid AND a.version_id IS NOT DISTINCT FROM (e->>'version_id')::uuid AND p.created_at=(e->>'created_at')::timestamptz) INTO valid;
  ELSIF e->>'kind'='company' THEN
   SELECT EXISTS(SELECT 1 FROM research_alerts a WHERE a.owner_id=NEW.owner_id AND a.id=(e->>'id')::uuid AND a.instrument_id=(e->>'instrument_id')::uuid AND a.version_id IS NOT DISTINCT FROM (e->>'version_id')::uuid AND a.created_at=(e->>'created_at')::timestamptz) INTO valid;
  ELSIF e->>'kind'='condition' THEN
   SELECT EXISTS(SELECT 1 FROM change_events a JOIN thesis_versions v ON v.id=a.version_id AND v.owner_id=a.owner_id JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id WHERE a.owner_id=NEW.owner_id AND a.id=(e->>'id')::uuid AND t.instrument_id=(e->>'instrument_id')::uuid AND a.version_id=(e->>'version_id')::uuid AND a.created_at=(e->>'created_at')::timestamptz) INTO valid;
  END IF;
  IF NOT valid OR (e->>'created_at')::timestamptz>NEW.scheduled_at OR (e->>'created_at')::timestamptz<=(NEW.manifest->>'window_start')::timestamptz THEN RAISE EXCEPTION 'Saved review event is outside its owner or period'; END IF;
 END LOOP;
 RETURN NEW;
END $$;
CREATE TRIGGER validate_membership BEFORE INSERT ON scheduled_reviews FOR EACH ROW EXECUTE FUNCTION scheduled_review_membership();
