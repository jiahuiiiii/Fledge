-- Weekly reviews include price-move events (since migration 059), but the
-- membership check only knew idea, company and condition records, so every
-- week with a price move failed to save (first seen 20 Oct 2026). Same checks
-- as 029, plus one branch: a move must be this owner's recorded event, for
-- the same primary company and creation time, with no idea version.
CREATE OR REPLACE FUNCTION scheduled_review_membership() RETURNS trigger LANGUAGE plpgsql AS $$
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
  ELSIF e->>'kind'='move' THEN
   SELECT EXISTS(SELECT 1 FROM move_events a WHERE a.owner_id=NEW.owner_id AND a.id=(e->>'id')::uuid AND a.instrument_id=(e->>'instrument_id')::uuid AND (e->>'version_id') IS NULL AND a.created_at=(e->>'created_at')::timestamptz) INTO valid;
  END IF;
  IF NOT valid OR (e->>'created_at')::timestamptz>NEW.scheduled_at OR (e->>'created_at')::timestamptz<=(NEW.manifest->>'window_start')::timestamptz THEN RAISE EXCEPTION 'Saved review event is outside its owner or period'; END IF;
 END LOOP;
 RETURN NEW;
END $$;
