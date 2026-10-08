-- Shared interpretations of an exact saved sentiment sample; no watch mutation.
CREATE TABLE discussion_theme_reviews (
 id uuid PRIMARY KEY,instrument_id uuid NOT NULL REFERENCES instruments,
 analysis_id uuid NOT NULL,request_key text NOT NULL UNIQUE,
 call_id uuid NOT NULL REFERENCES model_calls,packet jsonb NOT NULL,result jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(instrument_id,analysis_id) REFERENCES sentiment_analyses(instrument_id,id));
CREATE INDEX discussion_themes_history ON discussion_theme_reviews(instrument_id,created_at DESC,id DESC);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON discussion_theme_reviews FOR EACH ROW EXECUTE FUNCTION immutable_record();
GRANT SELECT,INSERT ON discussion_theme_reviews TO thesis_app;
