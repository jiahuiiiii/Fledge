INSERT INTO sources VALUES('finnhub-financials','Finnhub reported multiples','finnhub-pitch') ON CONFLICT DO NOTHING;
CREATE TABLE multiple_references (
 id uuid PRIMARY KEY, instrument_id uuid NOT NULL REFERENCES instruments, symbol text NOT NULL,
 metrics jsonb NOT NULL, payload jsonb NOT NULL, retrieved_at timestamptz NOT NULL
);
CREATE INDEX multiple_references_latest ON multiple_references(instrument_id,retrieved_at DESC);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON multiple_references FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TABLE multiple_refresh_state (
 instrument_id uuid PRIMARY KEY REFERENCES instruments, attempt_id uuid,last_attempt_at timestamptz,lease_until timestamptz,completed_at timestamptz,error text
);
GRANT SELECT ON multiple_references,multiple_refresh_state TO thesis_app;
GRANT SELECT,INSERT ON multiple_references,multiple_refresh_state TO thesis_source;
GRANT UPDATE ON multiple_refresh_state TO thesis_source;
CREATE TABLE valuation_scenarios (
 id uuid PRIMARY KEY,owner_id uuid NOT NULL REFERENCES accounts,instrument_id uuid NOT NULL REFERENCES instruments,
 performance_id uuid NOT NULL,request_id uuid NOT NULL,request_hash text NOT NULL,
 assumptions jsonb NOT NULL,packet jsonb NOT NULL,result jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id,id),UNIQUE(owner_id,request_id),
 FOREIGN KEY(performance_id,instrument_id) REFERENCES performance_snapshots(id,instrument_id)
);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON valuation_scenarios FOR EACH ROW EXECUTE FUNCTION immutable_record();
ALTER TABLE valuation_scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE valuation_scenarios FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON valuation_scenarios USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid) WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT ON valuation_scenarios TO thesis_app;
