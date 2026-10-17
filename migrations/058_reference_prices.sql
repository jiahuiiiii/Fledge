-- Price-only references must never enter the SEC company/instrument directory.
CREATE TABLE reference_instruments (
 symbol text PRIMARY KEY CHECK(symbol ~ '^[A-Z]{1,5}$'),
 name text NOT NULL,
 role text NOT NULL CHECK(role IN ('index','sector')),
 UNIQUE(symbol,role)
);
INSERT INTO reference_instruments VALUES
 ('QQQ','Nasdaq-100 fund','index'),
 ('SPY','S&P 500 fund','index'),
 ('SOXX','Semiconductor fund','sector');

CREATE TABLE reference_price_snapshots (
 id uuid PRIMARY KEY,
 symbol text NOT NULL REFERENCES reference_instruments,
 resource text NOT NULL CHECK(resource IN ('quote','history')),
 raw jsonb NOT NULL CHECK(octet_length(raw::text)<=4194304),
 payload jsonb NOT NULL,
 fingerprint text NOT NULL CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
 retrieved_at timestamptz NOT NULL,
 UNIQUE(symbol,resource,id)
);
CREATE INDEX reference_snapshot_latest ON reference_price_snapshots(symbol,resource,retrieved_at DESC,id DESC);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON reference_price_snapshots
 FOR EACH ROW EXECUTE FUNCTION immutable_record();

CREATE TABLE reference_refresh_state (
 symbol text NOT NULL REFERENCES reference_instruments,
 resource text NOT NULL CHECK(resource IN ('quote','history')),
 attempt_id uuid,last_attempt_at timestamptz,lease_until timestamptz,
 completed_at timestamptz,error text,current_id uuid,
 PRIMARY KEY(symbol,resource),
 FOREIGN KEY(symbol,resource,current_id) REFERENCES reference_price_snapshots(symbol,resource,id)
);
GRANT SELECT ON reference_instruments,reference_price_snapshots,reference_refresh_state TO thesis_app,thesis_source;
GRANT INSERT ON reference_price_snapshots TO thesis_source;
GRANT INSERT,UPDATE ON reference_refresh_state TO thesis_source;

-- Explicit null means the owner selected no sector reference. No preference backfill.
CREATE TABLE company_sector_references (
 owner_id uuid NOT NULL REFERENCES accounts ON DELETE CASCADE,
 instrument_id uuid NOT NULL REFERENCES instruments ON DELETE CASCADE,
 symbol text,
 role text NOT NULL DEFAULT 'sector' CHECK(role='sector'),
 updated_at timestamptz NOT NULL,
 PRIMARY KEY(owner_id,instrument_id),
 FOREIGN KEY(symbol,role) REFERENCES reference_instruments(symbol,role)
);
ALTER TABLE company_sector_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_sector_references FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON company_sector_references
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT,UPDATE ON company_sector_references TO thesis_app;
