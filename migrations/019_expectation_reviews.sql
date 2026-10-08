CREATE TABLE expectation_reviews (
 id uuid PRIMARY KEY, instrument_id uuid NOT NULL REFERENCES instruments,
 request_key text NOT NULL UNIQUE, call_id uuid REFERENCES model_calls,
 packet jsonb NOT NULL, result jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT,INSERT ON expectation_reviews TO thesis_app;
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON expectation_reviews FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE INDEX expectation_reviews_history ON expectation_reviews(instrument_id,created_at DESC,id DESC);
