-- Research statements are separate from the existing two monitoring metrics.
CREATE TABLE performance_snapshots (
 id uuid PRIMARY KEY,
 instrument_id uuid NOT NULL REFERENCES instruments,
 payload_id uuid NOT NULL REFERENCES source_payloads,
 method text NOT NULL,
 data jsonb NOT NULL,
 created_at timestamptz NOT NULL,
 UNIQUE(id,instrument_id)
);
CREATE TABLE performance_current (
 instrument_id uuid PRIMARY KEY REFERENCES instruments,
 snapshot_id uuid NOT NULL,
 checked_at timestamptz NOT NULL,
 FOREIGN KEY(snapshot_id,instrument_id) REFERENCES performance_snapshots(id,instrument_id)
);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON performance_snapshots FOR EACH ROW EXECUTE FUNCTION immutable_record();
GRANT SELECT ON performance_snapshots,performance_current TO thesis_app;
GRANT SELECT,INSERT ON performance_snapshots,performance_current TO thesis_source;
GRANT UPDATE ON performance_current TO thesis_source;
