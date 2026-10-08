-- Explicit, revision-pinned event checking within the existing news watch.
ALTER TABLE news_watches ADD COLUMN event_version_id uuid;
ALTER TABLE news_watches ADD FOREIGN KEY(owner_id,event_version_id) REFERENCES thesis_versions(owner_id,id);
ALTER TABLE watch_checks ADD COLUMN event_version_id uuid;
ALTER TABLE watch_checks ADD FOREIGN KEY(owner_id,event_version_id) REFERENCES thesis_versions(owner_id,id);
ALTER TABLE event_evidence_reviews ADD COLUMN automatic boolean NOT NULL DEFAULT false;
CREATE TABLE event_review_activations (
 owner_id uuid NOT NULL,review_id uuid PRIMARY KEY,version_id uuid NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(owner_id,review_id,version_id) REFERENCES event_evidence_reviews(owner_id,id,version_id)
);
ALTER TABLE event_review_activations ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_review_activations FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON event_review_activations USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid) WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT ON event_review_activations TO thesis_app;
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON event_review_activations FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE FUNCTION event_watch_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.event_version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM thesis_versions v JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id WHERE v.owner_id=NEW.owner_id AND v.id=NEW.event_version_id AND t.instrument_id=NEW.instrument_id AND v.status='monitoring' AND EXISTS(SELECT 1 FROM version_events e WHERE e.owner_id=v.owner_id AND e.version_id=v.id)) THEN RAISE EXCEPTION 'Event watch requires approved events for this owner and company'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER event_membership BEFORE INSERT OR UPDATE ON news_watches FOR EACH ROW EXECUTE FUNCTION event_watch_membership();
CREATE TRIGGER event_membership BEFORE INSERT ON watch_checks FOR EACH ROW EXECUTE FUNCTION event_watch_membership();
