-- Additive runtime state only; existing watch preferences and history keep
-- their meaning. The new worker is disabled until an operator enables it.
CREATE TABLE fast_watch_state (
 owner_id uuid NOT NULL, instrument_id uuid NOT NULL,
 next_check_at timestamptz NOT NULL, last_check_at timestamptz,
 claim_token uuid, lease_until timestamptz, error text,
 PRIMARY KEY(owner_id,instrument_id),
 FOREIGN KEY(owner_id,instrument_id) REFERENCES news_watches ON DELETE CASCADE
);
ALTER TABLE fast_watch_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE fast_watch_state FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON fast_watch_state
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT,UPDATE,DELETE ON fast_watch_state TO thesis_app;

ALTER TABLE watch_checks ADD COLUMN lane text NOT NULL DEFAULT 'combined'
 CHECK(lane IN ('combined','fast','slow'));
ALTER TABLE watch_checks DROP CONSTRAINT watch_checks_interval_minutes_check;
ALTER TABLE watch_checks ADD CHECK(interval_minutes IN (15,60,240));
ALTER TABLE watch_checks ADD CHECK(
 (lane='fast' AND interval_minutes IN (15,60)) OR
 (lane IN ('combined','slow') AND interval_minutes IN (60,240))
);

-- A semantic settings edit invalidates both workers. Baseline/schedule/lease
-- changes made by workers do not count as editing the owner's preferences.
CREATE FUNCTION invalidate_fast_watch() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (OLD.enabled,OLD.interval_minutes,OLD.match_idea,OLD.event_version_id,OLD.include_context,OLD.idea_purpose)
 IS DISTINCT FROM
 (NEW.enabled,NEW.interval_minutes,NEW.match_idea,NEW.event_version_id,NEW.include_context,NEW.idea_purpose) THEN
  DELETE FROM fast_watch_state WHERE owner_id=NEW.owner_id AND instrument_id=NEW.instrument_id;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER invalidate_fast_watch AFTER UPDATE ON news_watches
 FOR EACH ROW EXECUTE FUNCTION invalidate_fast_watch();

CREATE TABLE reddit_thread_checks (
 thread_key text PRIMARY KEY,
 feed_updated_at timestamptz NOT NULL,
 checked_at timestamptz NOT NULL,
 body bytea NOT NULL CHECK(octet_length(body)<=2000000)
);
CREATE TABLE hn_comment_checks (
 instrument_id uuid NOT NULL REFERENCES instruments ON DELETE CASCADE,
 post_key text NOT NULL,
 checked_at timestamptz NOT NULL,
 PRIMARY KEY(instrument_id,post_key)
);
GRANT SELECT ON reddit_thread_checks,hn_comment_checks TO thesis_app;
GRANT SELECT,INSERT,UPDATE ON reddit_thread_checks,hn_comment_checks TO thesis_source;
