-- Thesis local prototype. Fresh database only; supersedes the unapplied design draft.
CREATE TABLE schema_migrations(version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE accounts(id uuid PRIMARY KEY, label text NOT NULL);
CREATE TABLE instruments(id uuid PRIMARY KEY, symbol text UNIQUE NOT NULL, name text NOT NULL);
CREATE TABLE sources(id text PRIMARY KEY, name text NOT NULL, entitlement text NOT NULL CHECK(entitlement='fictional'));
CREATE TABLE documents(id uuid PRIMARY KEY, instrument_id uuid NOT NULL REFERENCES instruments, source_id text NOT NULL REFERENCES sources, url text UNIQUE NOT NULL);
CREATE TABLE document_versions(
 id uuid PRIMARY KEY, document_id uuid NOT NULL REFERENCES documents, content_hash text NOT NULL,
 headline text NOT NULL, body text NOT NULL, published_at timestamptz NOT NULL,
 available_at timestamptz NOT NULL, supersedes_id uuid,
 UNIQUE(document_id,content_hash), UNIQUE(id,document_id),
 FOREIGN KEY(supersedes_id,document_id) REFERENCES document_versions(id,document_id), CHECK(available_at>=published_at)
);
CREATE TABLE observations(
 id uuid PRIMARY KEY, instrument_id uuid NOT NULL REFERENCES instruments, document_version_id uuid NOT NULL REFERENCES document_versions,
 metric text NOT NULL CHECK(metric IN ('revenue_growth','operating_margin')), value numeric NOT NULL,
 unit text NOT NULL CHECK(unit='percent'), basis text NOT NULL CHECK(basis='reported'),
 period text NOT NULL, period_start date NOT NULL, period_end date NOT NULL, available_at timestamptz NOT NULL,
 supersedes_id uuid, UNIQUE(id,instrument_id,metric,period,unit,basis),
 FOREIGN KEY(supersedes_id,instrument_id,metric,period,unit,basis) REFERENCES observations(id,instrument_id,metric,period,unit,basis),
 CHECK(period_end>=period_start), CHECK(value BETWEEN -100 AND 1000)
);
CREATE TABLE claims(
 id uuid PRIMARY KEY, instrument_id uuid NOT NULL REFERENCES instruments, document_version_id uuid NOT NULL REFERENCES document_versions,
 kind text NOT NULL CHECK(kind IN ('reported','guidance','news_report','interpretation')), stance text NOT NULL CHECK(stance IN ('support','challenge','unknown')),
 title text NOT NULL, body text NOT NULL, quote text NOT NULL, event_key text NOT NULL, available_at timestamptz NOT NULL
);
CREATE TABLE source_checks(id uuid PRIMARY KEY, stage integer NOT NULL, source_id text NOT NULL REFERENCES sources,
 checked_at timestamptz NOT NULL, outcome text NOT NULL CHECK(outcome IN ('success','failed')), cursor text, covered_through timestamptz, error text);
CREATE TABLE demo_state(singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), stage integer NOT NULL DEFAULT 0 CHECK(stage BETWEEN 0 AND 4));
INSERT INTO demo_state VALUES(true,0);
CREATE TABLE theses(id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES accounts, instrument_id uuid NOT NULL REFERENCES instruments,
 revision integer NOT NULL DEFAULT 0, status text NOT NULL CHECK(status IN ('draft','monitoring','archived')), created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id,instrument_id), UNIQUE(owner_id,id));
CREATE TABLE thesis_versions(id uuid PRIMARY KEY, owner_id uuid NOT NULL, thesis_id uuid NOT NULL, revision integer NOT NULL,
 question text NOT NULL, reasoning text NOT NULL, status text NOT NULL CHECK(status IN ('draft','monitoring','archived')),
 created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(owner_id,thesis_id,revision), UNIQUE(owner_id,id),
 FOREIGN KEY(owner_id,thesis_id) REFERENCES theses(owner_id,id));
CREATE TABLE version_conditions(owner_id uuid NOT NULL, version_id uuid NOT NULL, condition_id uuid NOT NULL,
 metric text NOT NULL CHECK(metric IN ('revenue_growth','operating_margin')), operator text NOT NULL CHECK(operator IN ('>=','<=')),
 threshold numeric NOT NULL CHECK(threshold BETWEEN -100 AND 1000), unit text NOT NULL CHECK(unit='percent'), basis text NOT NULL CHECK(basis='reported'),
 period_type text NOT NULL CHECK(period_type='quarter'), PRIMARY KEY(owner_id,version_id,condition_id),
 FOREIGN KEY(owner_id,version_id) REFERENCES thesis_versions(owner_id,id));
CREATE TABLE jobs(id uuid PRIMARY KEY, owner_id uuid NOT NULL, version_id uuid NOT NULL, fingerprint text NOT NULL,
 manifest jsonb NOT NULL, status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','running','done','failed')),
 attempts integer NOT NULL DEFAULT 0, lease_until timestamptz, error text, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id,fingerprint), FOREIGN KEY(owner_id,version_id) REFERENCES thesis_versions(owner_id,id));
CREATE TABLE evaluations(id uuid PRIMARY KEY, owner_id uuid NOT NULL, version_id uuid NOT NULL, fingerprint text NOT NULL,
 manifest jsonb NOT NULL, outcome text NOT NULL CHECK(outcome IN ('met','not_met','unknown')), availability text NOT NULL,
 freshness text NOT NULL, disagreement boolean NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id,fingerprint), UNIQUE(owner_id,id,version_id), FOREIGN KEY(owner_id,version_id) REFERENCES thesis_versions(owner_id,id));
CREATE TABLE condition_results(owner_id uuid NOT NULL, evaluation_id uuid NOT NULL, version_id uuid NOT NULL, condition_id uuid NOT NULL,
 outcome text NOT NULL CHECK(outcome IN ('met','not_met','unknown')), observed_value numeric, observation_id uuid REFERENCES observations,
 explanation text NOT NULL, PRIMARY KEY(evaluation_id,condition_id),
 FOREIGN KEY(owner_id,evaluation_id,version_id) REFERENCES evaluations(owner_id,id,version_id),
 FOREIGN KEY(owner_id,version_id,condition_id) REFERENCES version_conditions(owner_id,version_id,condition_id));
CREATE TABLE review_events(id uuid PRIMARY KEY, owner_id uuid NOT NULL, evaluation_id uuid NOT NULL, version_id uuid NOT NULL,
 action text NOT NULL CHECK(action IN ('reviewed','unresolved')), created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id,evaluation_id), FOREIGN KEY(owner_id,evaluation_id,version_id) REFERENCES evaluations(owner_id,id,version_id));
CREATE TABLE research_actions(id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES accounts, instrument_id uuid NOT NULL REFERENCES instruments,
 question text NOT NULL, action text NOT NULL CHECK(action IN ('investigate','unresolved','reject')), created_at timestamptz NOT NULL DEFAULT now());

CREATE FUNCTION immutable_record() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Historical records are append-only'; END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['document_versions','observations','claims','source_checks','thesis_versions','version_conditions','evaluations','condition_results','review_events','research_actions'] LOOP
 EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION immutable_record()',t);
 END LOOP;
END $$;
CREATE FUNCTION complete_evaluation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected integer; actual integer;
BEGIN
 SELECT count(*) INTO expected FROM version_conditions WHERE owner_id=NEW.owner_id AND version_id=NEW.version_id;
 SELECT count(*) INTO actual FROM condition_results WHERE owner_id=NEW.owner_id AND evaluation_id=NEW.id;
 IF expected=0 OR expected<>actual THEN RAISE EXCEPTION 'Evaluation must contain every condition result'; END IF;
 RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER complete_results AFTER INSERT ON evaluations DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION complete_evaluation();

DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['theses','thesis_versions','version_conditions','jobs','evaluations','condition_results','review_events','research_actions'] LOOP
 EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY account_scope ON %I USING (owner_id = nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK (owner_id = nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
 END LOOP;
END $$;
CREATE ROLE thesis_app LOGIN NOSUPERUSER NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO thesis_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO thesis_app;
GRANT INSERT ON theses,thesis_versions,version_conditions,jobs,evaluations,condition_results,review_events,research_actions TO thesis_app;
GRANT UPDATE ON theses,jobs TO thesis_app;
INSERT INTO schema_migrations(version) VALUES(1);
