-- New public structured-filing scope. This does not enable third-party news or model use.
ALTER TABLE sources DROP CONSTRAINT sources_entitlement_check;
ALTER TABLE sources ADD CHECK(entitlement IN ('fictional','sec-public'));
ALTER TABLE instrument_state ADD COLUMN period_type text NOT NULL DEFAULT 'quarter' CHECK(period_type IN ('quarter','annual'));
CREATE TABLE fact_scopes(observation_id uuid PRIMARY KEY REFERENCES observations,period_type text NOT NULL CHECK(period_type IN ('quarter','annual')),period_convention text NOT NULL CHECK(period_convention IN ('calendar','filing-dates')));
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fact_scopes FOR EACH ROW EXECUTE FUNCTION immutable_record();
GRANT SELECT ON fact_scopes TO thesis_app;
ALTER TABLE version_conditions DROP CONSTRAINT version_conditions_period_type_check;
ALTER TABLE version_conditions ADD CHECK(period_type IN ('quarter','annual'));
CREATE TABLE sec_companies(instrument_id uuid PRIMARY KEY REFERENCES instruments,cik bigint NOT NULL UNIQUE CHECK(cik>0));
CREATE TABLE source_payloads(id uuid PRIMARY KEY,instrument_id uuid NOT NULL REFERENCES instruments,
 content_hash text NOT NULL,payload jsonb NOT NULL,retrieved_at timestamptz NOT NULL,
 UNIQUE(instrument_id,content_hash));
CREATE TABLE filing_calculations(document_version_id uuid PRIMARY KEY REFERENCES document_versions,
 payload_id uuid NOT NULL REFERENCES source_payloads,accession text NOT NULL,form text NOT NULL,
 filing_url text NOT NULL,period_type text NOT NULL,period_start date,period_end date NOT NULL,
 calculations jsonb NOT NULL,raw_facts jsonb NOT NULL,limitations jsonb NOT NULL);
CREATE TABLE sec_refresh_state(instrument_id uuid PRIMARY KEY REFERENCES instruments,
 attempt_id uuid,last_attempt_at timestamptz,lease_until timestamptz,last_error text);
CREATE TABLE source_request_clock(singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),next_at timestamptz NOT NULL DEFAULT now());
INSERT INTO source_request_clock VALUES(true,now());
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON source_payloads FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON filing_calculations FOR EACH ROW EXECUTE FUNCTION immutable_record();
GRANT SELECT ON sec_companies,source_payloads,filing_calculations,sec_refresh_state TO thesis_app;
-- Collector has shared-source permissions only, never private ideas or model accounting.
DO $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='thesis_source') THEN
  CREATE ROLE thesis_source LOGIN NOSUPERUSER NOBYPASSRLS;
 END IF;
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='thesis_source' AND (rolsuper OR rolbypassrls)) THEN
  RAISE EXCEPTION 'Source role must be restricted';
 END IF;
END $$;
GRANT USAGE ON SCHEMA public TO thesis_source;
GRANT SELECT,INSERT ON instruments,sources,instrument_state,instrument_sources,documents,document_versions,observations,fact_scopes,claims,document_lineage,source_checks,research_snapshots,sec_companies,source_payloads,filing_calculations,sec_refresh_state TO thesis_source;
GRANT SELECT,UPDATE ON source_request_clock TO thesis_source;
GRANT UPDATE ON instrument_state,sec_refresh_state TO thesis_source;
GRANT USAGE ON SEQUENCE research_snapshots_id_seq TO thesis_source;
