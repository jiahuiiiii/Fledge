-- Separate data-source access from the unchanged model allowance.
ALTER TABLE sources DROP CONSTRAINT sources_entitlement_check;
ALTER TABLE sources ADD CONSTRAINT sources_entitlement_check CHECK(entitlement IN ('fictional','sec-public','finnhub-pitch','public-news','local-yahoo-history','local-stockanalysis-targets','fmp-local'));
INSERT INTO sources VALUES('fmp-profile','FMP company profiles','fmp-local'),('fmp-peers','FMP suggested peers','fmp-local'),('fmp-estimates','FMP analyst consensus','fmp-local'),('fmp-ratios','FMP trailing ratios','fmp-local');
CREATE TABLE fmp_snapshots(
 id uuid PRIMARY KEY,dataset text NOT NULL CHECK(dataset IN ('profile','peers','estimates','ratios')),
 symbol text NOT NULL,source_id text NOT NULL REFERENCES sources,content_hash text NOT NULL,
 payload jsonb NOT NULL,data jsonb NOT NULL,available_at timestamptz NOT NULL,
 UNIQUE(dataset,symbol,content_hash),UNIQUE(id,dataset,symbol)
);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fmp_snapshots FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TABLE fmp_current(
 dataset text NOT NULL,symbol text NOT NULL,snapshot_id uuid NOT NULL,checked_at timestamptz NOT NULL,
 PRIMARY KEY(dataset,symbol),FOREIGN KEY(snapshot_id,dataset,symbol) REFERENCES fmp_snapshots(id,dataset,symbol)
);
CREATE TABLE fmp_refresh_state(
 dataset text NOT NULL,symbol text NOT NULL,attempt_id uuid,last_attempt_at timestamptz,lease_until timestamptz,last_success_at timestamptz,error text,PRIMARY KEY(dataset,symbol)
);
GRANT SELECT ON fmp_snapshots,fmp_current,fmp_refresh_state TO thesis_app;
GRANT SELECT,INSERT ON fmp_snapshots,fmp_current,fmp_refresh_state TO thesis_source;
GRANT UPDATE ON fmp_current,fmp_refresh_state TO thesis_source;
CREATE TABLE peer_selections(
 owner_id uuid NOT NULL REFERENCES accounts,instrument_id uuid NOT NULL REFERENCES instruments,
 symbol text NOT NULL,rationale text NOT NULL CHECK(length(rationale) BETWEEN 8 AND 600),updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(owner_id,instrument_id,symbol)
);
ALTER TABLE peer_selections ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_selections FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON peer_selections USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid) WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT,UPDATE,DELETE ON peer_selections TO thesis_app;
