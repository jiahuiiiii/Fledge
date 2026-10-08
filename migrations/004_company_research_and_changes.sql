-- Existing Northstar history remains valid; new work is explicitly company-scoped.
INSERT INTO instruments(id,symbol,name) VALUES('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','NSTR','Northstar Software') ON CONFLICT DO NOTHING;
CREATE TABLE instrument_state(
 instrument_id uuid PRIMARY KEY REFERENCES instruments,
 cutoff timestamptz NOT NULL, period text NOT NULL, sequence integer NOT NULL DEFAULT 0,
 label text NOT NULL, mode text NOT NULL DEFAULT 'recorded', sector text NOT NULL DEFAULT '',
 scenario_complete boolean NOT NULL DEFAULT false
);
INSERT INTO instrument_state(instrument_id,cutoff,period,sequence,label,sector,scenario_complete)
 SELECT 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
 (ARRAY['2025-07-24T12:00:00Z','2025-10-18T14:05:00Z','2025-10-24T12:00:00Z','2025-10-25T12:00:00Z','2025-10-28T12:00:00Z'])[stage+1]::timestamptz,
 CASE WHEN stage<2 THEN '2025-Q2' ELSE '2025-Q3' END,stage,
 (ARRAY['Q2 baseline','Renewal report','Q3 results','Source outage','Revenue restatement'])[stage+1],
 'Enterprise software',stage=4 FROM demo_state;
CREATE TABLE instrument_sources(instrument_id uuid NOT NULL REFERENCES instruments,source_id text NOT NULL REFERENCES sources,
 PRIMARY KEY(instrument_id,source_id));
INSERT INTO instrument_sources SELECT 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',id FROM sources;
ALTER TABLE source_checks ADD COLUMN instrument_id uuid NOT NULL DEFAULT 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa' REFERENCES instruments;
ALTER TABLE source_checks DROP CONSTRAINT source_checks_outcome_check;
ALTER TABLE source_checks ADD CHECK(outcome IN ('success','failed','denied'));
ALTER TABLE source_checks ADD COLUMN received_at timestamptz NOT NULL DEFAULT clock_timestamp();
CREATE INDEX source_checks_company_time ON source_checks(instrument_id,source_id,checked_at DESC);
CREATE TABLE document_lineage(document_version_id uuid PRIMARY KEY REFERENCES document_versions,
 origin_key text NOT NULL,story_key text NOT NULL,body_hash text NOT NULL);
INSERT INTO document_lineage SELECT v.id,d.source_id,c.event_key,encode(sha256(convert_to(v.body,'UTF8')),'hex') FROM document_versions v
 JOIN documents d ON d.id=v.document_id
 JOIN LATERAL(SELECT event_key FROM claims WHERE document_version_id=v.id LIMIT 1)c ON true;
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON document_lineage FOR EACH ROW EXECUTE FUNCTION immutable_record();
ALTER TABLE jobs ADD COLUMN input_signature text;
CREATE INDEX job_material_input ON jobs(owner_id,version_id,input_signature) WHERE input_signature IS NOT NULL;
CREATE TABLE change_events(
 id uuid PRIMARY KEY,owner_id uuid NOT NULL,version_id uuid NOT NULL,evaluation_id uuid NOT NULL,
 previous_evaluation_id uuid NOT NULL,kind text NOT NULL,summary text NOT NULL,details jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(owner_id,evaluation_id),
 FOREIGN KEY(owner_id,evaluation_id,version_id) REFERENCES evaluations(owner_id,id,version_id),
 FOREIGN KEY(owner_id,previous_evaluation_id,version_id) REFERENCES evaluations(owner_id,id,version_id)
);
ALTER TABLE change_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE change_events FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON change_events USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON change_events FOR EACH ROW EXECUTE FUNCTION immutable_record();
GRANT SELECT ON instrument_state,instrument_sources,document_lineage,change_events TO thesis_app;
GRANT INSERT ON change_events TO thesis_app;

CREATE TABLE research_snapshots(id bigserial PRIMARY KEY,instrument_id uuid NOT NULL REFERENCES instruments,
 cutoff timestamptz NOT NULL,payload jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX snapshot_company_order ON research_snapshots(instrument_id,id);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON research_snapshots FOR EACH ROW EXECUTE FUNCTION immutable_record();
ALTER TABLE thesis_versions ADD COLUMN start_snapshot bigint NOT NULL DEFAULT 0;
CREATE TABLE monitoring_cursors(owner_id uuid NOT NULL,version_id uuid NOT NULL,last_snapshot bigint NOT NULL,
 PRIMARY KEY(owner_id,version_id),FOREIGN KEY(owner_id,version_id) REFERENCES thesis_versions(owner_id,id));
ALTER TABLE monitoring_cursors ENABLE ROW LEVEL SECURITY;
ALTER TABLE monitoring_cursors FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON monitoring_cursors USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT ON research_snapshots,monitoring_cursors TO thesis_app;
GRANT INSERT,UPDATE ON monitoring_cursors TO thesis_app;
