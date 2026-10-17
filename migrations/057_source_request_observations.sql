-- Status codes only: no request URLs, credentials, response text or identities.
CREATE TABLE source_request_events (
 id uuid PRIMARY KEY,
 check_id uuid REFERENCES watch_checks(id) ON DELETE CASCADE,
 provider text NOT NULL CHECK(provider ~ '^[a-z_]{1,40}$'),
 observed_at timestamptz NOT NULL,
 http_status integer NOT NULL CHECK(http_status BETWEEN 100 AND 599)
);
CREATE INDEX source_request_events_window ON source_request_events(observed_at,provider);
ALTER TABLE source_request_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_request_events FORCE ROW LEVEL SECURITY;
CREATE POLICY source_scope ON source_request_events TO thesis_source USING(true) WITH CHECK(true);
CREATE POLICY account_scope ON source_request_events TO thesis_app
 USING(check_id IS NULL OR EXISTS(
  SELECT 1 FROM watch_checks c WHERE c.id=check_id
  AND c.owner_id=nullif(current_setting('app.user_id',true),'')::uuid
 ));
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON source_request_events
 FOR EACH ROW EXECUTE FUNCTION immutable_record();
GRANT SELECT ON source_request_events TO thesis_app,thesis_source;
GRANT INSERT ON source_request_events TO thesis_source;
