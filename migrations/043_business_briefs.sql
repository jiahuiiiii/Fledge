CREATE TABLE business_briefs (
 id uuid PRIMARY KEY, instrument_id uuid NOT NULL REFERENCES instruments,
 request_key text NOT NULL UNIQUE, call_id uuid NOT NULL REFERENCES model_calls,
 packet jsonb NOT NULL, result jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON business_briefs
 FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE INDEX business_briefs_history ON business_briefs(instrument_id,created_at DESC,id DESC);
GRANT SELECT,INSERT ON business_briefs TO thesis_app;
