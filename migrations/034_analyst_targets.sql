ALTER TABLE sources DROP CONSTRAINT sources_entitlement_check;
ALTER TABLE sources ADD CONSTRAINT sources_entitlement_check CHECK(entitlement IN ('fictional','sec-public','finnhub-pitch','local-yahoo-history','local-stockanalysis-targets'));
INSERT INTO sources VALUES('stockanalysis-targets','Stock Analysis / S&P Global analyst targets','local-stockanalysis-targets') ON CONFLICT DO NOTHING;
CREATE TABLE analyst_target_snapshots (
 id uuid PRIMARY KEY, instrument_id uuid NOT NULL REFERENCES instruments,
 data jsonb NOT NULL, retrieved_at timestamptz NOT NULL
);
CREATE INDEX analyst_target_latest ON analyst_target_snapshots(instrument_id,retrieved_at DESC);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON analyst_target_snapshots FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TABLE analyst_target_state (
 instrument_id uuid PRIMARY KEY REFERENCES instruments,
 attempt_id uuid, last_attempt_at timestamptz, lease_until timestamptz,
 completed_at timestamptz, error text
);
CREATE TABLE analyst_target_clock(singleton boolean PRIMARY KEY CHECK(singleton),next_at timestamptz NOT NULL);
INSERT INTO analyst_target_clock VALUES(true,now());
GRANT SELECT ON analyst_target_snapshots,analyst_target_state TO thesis_app;
GRANT SELECT,INSERT ON analyst_target_snapshots,analyst_target_state TO thesis_source;
GRANT UPDATE ON analyst_target_state TO thesis_source;
GRANT SELECT,UPDATE ON analyst_target_clock TO thesis_source;
