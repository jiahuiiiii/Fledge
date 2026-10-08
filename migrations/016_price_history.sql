ALTER TABLE sources DROP CONSTRAINT sources_entitlement_check;
ALTER TABLE sources ADD CHECK(entitlement IN ('fictional','sec-public','finnhub-pitch','local-yahoo-history'));
INSERT INTO sources VALUES('yahoo-price-history','Yahoo Finance daily prices','local-yahoo-history') ON CONFLICT DO NOTHING;
CREATE TABLE price_history_snapshots (
 id uuid PRIMARY KEY,instrument_id uuid NOT NULL REFERENCES instruments,
 symbol text NOT NULL,payload jsonb NOT NULL,series jsonb NOT NULL,
 payload_hash text NOT NULL,retrieved_at timestamptz NOT NULL,
 UNIQUE(instrument_id,id)
);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON price_history_snapshots FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TABLE price_history_state (
 instrument_id uuid PRIMARY KEY REFERENCES instruments,current_id uuid,
 attempt_id uuid,last_attempt_at timestamptz,lease_until timestamptz,completed_at timestamptz,error text,
 FOREIGN KEY(instrument_id,current_id) REFERENCES price_history_snapshots(instrument_id,id)
);
CREATE TABLE price_history_clock(singleton boolean PRIMARY KEY CHECK(singleton),next_at timestamptz NOT NULL);
INSERT INTO price_history_clock VALUES(true,now());
GRANT SELECT ON price_history_snapshots,price_history_state TO thesis_app;
GRANT SELECT,INSERT ON price_history_snapshots,price_history_state TO thesis_source;
GRANT UPDATE ON price_history_state TO thesis_source;
GRANT SELECT,UPDATE ON price_history_clock TO thesis_source;
