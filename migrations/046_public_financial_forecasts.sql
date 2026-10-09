-- Financial forecasts share the existing public page's request clock and leases.
ALTER TABLE sources DROP CONSTRAINT sources_entitlement_check;
ALTER TABLE sources ADD CONSTRAINT sources_entitlement_check CHECK(entitlement IN ('fictional','sec-public','finnhub-pitch','public-news','local-yahoo-history','local-stockanalysis-targets','local-stockanalysis-forecasts','fmp-local'));
INSERT INTO sources VALUES('stockanalysis-forecasts','Stock Analysis / S&P Global financial forecasts','local-stockanalysis-forecasts');
CREATE TABLE public_financial_forecasts (
 id uuid PRIMARY KEY, instrument_id uuid NOT NULL REFERENCES instruments,
 observed_at timestamptz NOT NULL, page_sha256 text NOT NULL,
 html text NOT NULL CHECK(octet_length(html)<=2000000),
 data jsonb, error text,
 CHECK((data IS NOT NULL AND error IS NULL) OR (data IS NULL AND error IS NOT NULL))
);
CREATE INDEX public_financial_forecasts_latest ON public_financial_forecasts(instrument_id,observed_at DESC);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON public_financial_forecasts FOR EACH ROW EXECUTE FUNCTION immutable_record();
GRANT SELECT(id,instrument_id,observed_at,page_sha256,data,error) ON public_financial_forecasts TO thesis_app;
GRANT SELECT,INSERT ON public_financial_forecasts TO thesis_source;
