-- Local pitch MVP: bounded Finnhub news and quotes; the original budget is unchanged.
ALTER TABLE sources DROP CONSTRAINT sources_entitlement_check;
ALTER TABLE sources ADD CHECK(entitlement IN ('fictional','sec-public','finnhub-pitch'));
ALTER TABLE documents DROP CONSTRAINT documents_url_key;
ALTER TABLE documents ADD UNIQUE(instrument_id,source_id,url);
INSERT INTO sources VALUES('finnhub-news','Finnhub company news','finnhub-pitch');
CREATE TABLE market_articles(document_version_id uuid PRIMARY KEY REFERENCES document_versions,
 publisher text NOT NULL,provider_id text NOT NULL);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON market_articles FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TABLE market_quotes(id uuid PRIMARY KEY,instrument_id uuid NOT NULL REFERENCES instruments,
 quote jsonb NOT NULL,retrieved_at timestamptz NOT NULL);
CREATE INDEX market_quote_latest ON market_quotes(instrument_id,retrieved_at DESC);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON market_quotes FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TABLE market_refresh_state(instrument_id uuid PRIMARY KEY REFERENCES instruments,
 attempt_id uuid,last_attempt_at timestamptz,lease_until timestamptz,completed_at timestamptz,
 quote_error text,news_error text,news_count integer,excluded_count integer);
CREATE TABLE market_request_clock(singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),next_at timestamptz NOT NULL);
INSERT INTO market_request_clock VALUES(true,now());
GRANT SELECT ON market_articles,market_quotes,market_refresh_state TO thesis_app;
GRANT SELECT,INSERT ON market_articles,market_quotes,market_refresh_state TO thesis_source;
GRANT UPDATE ON market_refresh_state TO thesis_source;
GRANT SELECT,UPDATE ON market_request_clock TO thesis_source;
