-- Original filing text is separate from structured facts and private research.
CREATE TABLE sec_payload_current (
 instrument_id uuid PRIMARY KEY REFERENCES instruments,
 payload_id uuid NOT NULL REFERENCES source_payloads,
 checked_at timestamptz NOT NULL
);
-- Existing saved performance identifies the best retained payload at upgrade.
-- This is a backfill, never a new provider check or backdated availability.
INSERT INTO sec_payload_current SELECT c.instrument_id,p.payload_id,c.checked_at
 FROM performance_current c JOIN performance_snapshots p ON p.id=c.snapshot_id;
GRANT SELECT ON sec_payload_current TO thesis_app;
GRANT SELECT,INSERT,UPDATE ON sec_payload_current TO thesis_source;
CREATE TABLE disclosure_documents (
 id uuid PRIMARY KEY, instrument_id uuid NOT NULL REFERENCES instruments,
 source_id text NOT NULL REFERENCES sources, slot text NOT NULL,
 accession text NOT NULL, form text NOT NULL, url text NOT NULL,
 headline text NOT NULL, published_at timestamptz NOT NULL,
 available_at timestamptz NOT NULL, content_hash text NOT NULL,
 raw_html bytea NOT NULL, data jsonb NOT NULL,
 UNIQUE(id,instrument_id), UNIQUE(instrument_id,url,content_hash)
);
CREATE TABLE disclosure_current (
 instrument_id uuid NOT NULL REFERENCES instruments, slot text NOT NULL,
 document_id uuid NOT NULL, checked_at timestamptz NOT NULL,
 PRIMARY KEY(instrument_id,slot),
 FOREIGN KEY(document_id,instrument_id) REFERENCES disclosure_documents(id,instrument_id)
);
CREATE TABLE disclosure_refresh_state (
 instrument_id uuid PRIMARY KEY REFERENCES instruments,
 attempt_id uuid, last_attempt_at timestamptz, lease_until timestamptz,
 last_success_at timestamptz, last_error text, coverage jsonb NOT NULL DEFAULT '[]'
);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON disclosure_documents
 FOR EACH ROW EXECUTE FUNCTION immutable_record();
GRANT SELECT ON disclosure_documents,disclosure_current,disclosure_refresh_state TO thesis_app;
GRANT SELECT,INSERT ON disclosure_documents,disclosure_current,disclosure_refresh_state TO thesis_source;
GRANT UPDATE ON disclosure_current,disclosure_refresh_state TO thesis_source;
INSERT INTO sources(id,name,entitlement) VALUES('sec-disclosures','SEC original filings and earnings releases','sec-public');
