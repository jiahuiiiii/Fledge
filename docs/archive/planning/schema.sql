-- Finance product: PostgreSQL reference schema, 1 October 2026.
-- New, empty database only. This is NOT a migration for either existing app.
-- No extensions, credentials, production roles or data are installed here.
-- See database-design.md for API contracts and service invariants.
BEGIN;
CREATE SCHEMA finance;
SET LOCAL search_path = finance, public;

CREATE TABLE accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_subject text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE instruments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name text NOT NULL,
    cik text,
    exchange_code text NOT NULL,
    currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE symbol_aliases (
    instrument_id uuid NOT NULL REFERENCES instruments(id),
    exchange_code text NOT NULL,
    symbol text NOT NULL,
    valid_from date NOT NULL,
    valid_to date,
    PRIMARY KEY (exchange_code, symbol, valid_from),
    CHECK (valid_to IS NULL OR valid_to > valid_from)
);
CREATE UNIQUE INDEX current_symbol ON symbol_aliases(exchange_code, symbol)
    WHERE valid_to IS NULL;

CREATE TABLE sources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL UNIQUE,
    kind text NOT NULL CHECK (kind IN ('filing','news','market_data','social','company')),
    entitlement_scope text NOT NULL,
    retention_policy jsonb NOT NULL DEFAULT '{}',
    enabled boolean NOT NULL DEFAULT false
);
CREATE TABLE documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES sources(id),
    canonical_url text NOT NULL,
    external_id text,
    UNIQUE (source_id, canonical_url)
);
CREATE TABLE document_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES documents(id),
    content_hash text NOT NULL,
    title text NOT NULL,
    published_at timestamptz,
    first_seen_at timestamptz NOT NULL,
    fetched_at timestamptz NOT NULL,
    permitted_text text,
    origin_cluster_key text,
    language text,
    supersedes_id uuid REFERENCES document_versions(id),
    UNIQUE (document_id, content_hash),
    CHECK (fetched_at >= first_seen_at)
);
CREATE TABLE document_instruments (
    document_version_id uuid NOT NULL REFERENCES document_versions(id),
    instrument_id uuid NOT NULL REFERENCES instruments(id),
    relevance numeric CHECK (relevance BETWEEN 0 AND 1),
    PRIMARY KEY (document_version_id, instrument_id)
);

CREATE TABLE metric_definitions (
    key text PRIMARY KEY,
    label text NOT NULL,
    unit text NOT NULL,
    definition text NOT NULL,
    definition_version text NOT NULL
);
CREATE TABLE metric_observations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id uuid NOT NULL REFERENCES instruments(id),
    metric_key text NOT NULL REFERENCES metric_definitions(key),
    source_id uuid NOT NULL REFERENCES sources(id),
    source_record_key text NOT NULL,
    source_revision text NOT NULL,
    document_version_id uuid REFERENCES document_versions(id),
    value numeric NOT NULL,
    currency text CHECK (currency ~ '^[A-Z]{3}$'),
    period_start date,
    period_end date,
    period_kind text NOT NULL CHECK (period_kind IN ('instant','quarter','annual','ttm','forward')),
    observed_at timestamptz NOT NULL,
    available_at timestamptz NOT NULL,
    first_seen_at timestamptz NOT NULL,
    calculation_version text,
    supersedes_id uuid REFERENCES metric_observations(id),
    UNIQUE (source_id, source_record_key, source_revision),
    CHECK (period_start IS NULL OR period_end >= period_start)
);
CREATE INDEX metric_lookup ON metric_observations(instrument_id, metric_key, available_at DESC);

-- Company research contains no private thesis text. Its source entitlements
-- must still be enforced by the API; public company does not mean public data.
CREATE TABLE research_briefs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id uuid NOT NULL REFERENCES instruments(id),
    evidence_cutoff timestamptz NOT NULL,
    methodology_version text NOT NULL,
    input_fingerprint text NOT NULL,
    entitlement_scope text NOT NULL,
    sections jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (instrument_id, input_fingerprint, methodology_version, entitlement_scope)
);
CREATE TABLE brief_evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    brief_id uuid NOT NULL REFERENCES research_briefs(id),
    section_key text NOT NULL,
    document_version_id uuid REFERENCES document_versions(id),
    metric_observation_id uuid REFERENCES metric_observations(id),
    relation text NOT NULL CHECK (relation IN ('supports','contradicts','context')),
    quoted_text text,
    CHECK (num_nonnulls(document_version_id, metric_observation_id) = 1)
);

CREATE TABLE theses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES accounts(id),
    instrument_id uuid NOT NULL REFERENCES instruments(id),
    current_version_id uuid,
    archived_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (owner_id, id)
);
CREATE TABLE thesis_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL,
    thesis_id uuid NOT NULL,
    revision integer NOT NULL CHECK (revision > 0),
    title text NOT NULL,
    argument text NOT NULL,
    notes text,
    quant_mode text NOT NULL CHECK (quant_mode IN ('AND','OR')),
    catalyst_mode text NOT NULL CHECK (catalyst_mode IN ('AND','OR')),
    horizon_end timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (owner_id, thesis_id) REFERENCES theses(owner_id, id),
    UNIQUE (owner_id, thesis_id, id),
    UNIQUE (thesis_id, revision)
);
ALTER TABLE theses ADD CONSTRAINT current_thesis_version
    FOREIGN KEY (owner_id, id, current_version_id)
    REFERENCES thesis_versions(owner_id, thesis_id, id) DEFERRABLE INITIALLY DEFERRED;

-- Stable condition identity is separate from an immutable semantic version.
CREATE TABLE conditions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL,
    thesis_id uuid NOT NULL,
    kind text NOT NULL CHECK (kind IN ('quant','catalyst')),
    FOREIGN KEY (owner_id, thesis_id) REFERENCES theses(owner_id, id),
    UNIQUE (owner_id, thesis_id, id, kind)
);
CREATE TABLE condition_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL,
    thesis_id uuid NOT NULL,
    condition_id uuid NOT NULL,
    kind text NOT NULL,
    revision integer NOT NULL CHECK (revision > 0),
    role text NOT NULL CHECK (role IN ('support','invalidation')),
    metric_key text REFERENCES metric_definitions(key),
    operator text CHECK (operator IN ('<','<=','=','!=','>=','>')),
    threshold numeric,
    description text,
    scope jsonb NOT NULL DEFAULT '{}',
    deadline timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (owner_id, thesis_id, condition_id, kind)
        REFERENCES conditions(owner_id, thesis_id, id, kind),
    UNIQUE (condition_id, revision),
    UNIQUE (owner_id, thesis_id, condition_id, id),
    CHECK (
        (kind = 'quant' AND metric_key IS NOT NULL AND operator IS NOT NULL
            AND threshold IS NOT NULL AND description IS NULL)
        OR (kind = 'catalyst' AND metric_key IS NULL AND operator IS NULL
            AND threshold IS NULL AND description IS NOT NULL)
    )
);
CREATE TABLE thesis_version_conditions (
    owner_id uuid NOT NULL,
    thesis_id uuid NOT NULL,
    thesis_version_id uuid NOT NULL,
    condition_id uuid NOT NULL,
    condition_version_id uuid NOT NULL,
    display_order integer NOT NULL DEFAULT 0,
    PRIMARY KEY (thesis_version_id, condition_id),
    UNIQUE (owner_id, thesis_id, thesis_version_id, condition_version_id),
    FOREIGN KEY (owner_id, thesis_id, thesis_version_id)
        REFERENCES thesis_versions(owner_id, thesis_id, id),
    FOREIGN KEY (owner_id, thesis_id, condition_id, condition_version_id)
        REFERENCES condition_versions(owner_id, thesis_id, condition_id, id)
);

CREATE TABLE evaluations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL,
    thesis_id uuid NOT NULL,
    thesis_version_id uuid NOT NULL,
    evidence_cutoff timestamptz NOT NULL,
    input_fingerprint text NOT NULL,
    evaluator_version text NOT NULL,
    status text NOT NULL CHECK (status IN ('met','not_met','unknown')),
    coverage text NOT NULL CHECK (coverage IN ('complete','partial','unavailable')),
    risk_state text NOT NULL CHECK (risk_state IN ('clear','flagged','unknown')),
    reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (owner_id, thesis_id, thesis_version_id)
        REFERENCES thesis_versions(owner_id, thesis_id, id),
    UNIQUE (owner_id, thesis_id, thesis_version_id, id),
    UNIQUE (owner_id, thesis_id, id),
    UNIQUE (thesis_version_id, input_fingerprint, evaluator_version)
);
CREATE TABLE condition_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL,
    thesis_id uuid NOT NULL,
    thesis_version_id uuid NOT NULL,
    evaluation_id uuid NOT NULL,
    condition_version_id uuid NOT NULL,
    outcome text NOT NULL CHECK (outcome IN ('pass','fail','unknown')),
    observed_value numeric,
    metric_observation_id uuid REFERENCES metric_observations(id),
    catalyst_state text CHECK (catalyst_state IN ('unconfirmed','rumored','confirmed','invalidated')),
    coverage text NOT NULL CHECK (coverage IN ('fresh','stale','missing','conflicting')),
    reasoning text,
    assessed_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (owner_id, thesis_id, thesis_version_id, evaluation_id)
        REFERENCES evaluations(owner_id, thesis_id, thesis_version_id, id),
    FOREIGN KEY (owner_id, thesis_id, thesis_version_id, condition_version_id)
        REFERENCES thesis_version_conditions(owner_id, thesis_id, thesis_version_id, condition_version_id),
    UNIQUE (owner_id, id),
    UNIQUE (evaluation_id, condition_version_id),
    CHECK (catalyst_state IS NULL OR (observed_value IS NULL AND metric_observation_id IS NULL))
);
CREATE TABLE result_evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL,
    condition_result_id uuid NOT NULL,
    document_version_id uuid NOT NULL REFERENCES document_versions(id),
    relation text NOT NULL CHECK (relation IN ('supports','contradicts','context')),
    quoted_text text,
    quote_start integer,
    quote_end integer,
    quote_verified boolean NOT NULL DEFAULT false,
    confidence numeric CHECK (confidence BETWEEN 0 AND 1),
    reasoning text,
    FOREIGN KEY (owner_id, condition_result_id) REFERENCES condition_results(owner_id, id),
    CHECK ((quote_start IS NULL AND quote_end IS NULL)
        OR (quote_start IS NOT NULL AND quote_end IS NOT NULL AND quote_start >= 0 AND quote_end > quote_start))
);

-- One proposal lifecycle, projected into the current UI's three groups.
CREATE TABLE proposals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES accounts(id),
    instrument_id uuid NOT NULL REFERENCES instruments(id),
    target_thesis_id uuid,
    base_version_id uuid,
    target_condition_id uuid,
    kind text NOT NULL CHECK (kind IN ('thesis','quant','catalyst')),
    operation text NOT NULL CHECK (operation IN ('ADD','UPDATE','REMOVE')),
    proposed_change jsonb NOT NULL,
    rationale text NOT NULL,
    source_document_version_id uuid REFERENCES document_versions(id),
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected','stale')),
    rejection_reason text,
    accepted_thesis_id uuid,
    accepted_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    resolved_at timestamptz,
    FOREIGN KEY (owner_id, target_thesis_id, base_version_id)
        REFERENCES thesis_versions(owner_id, thesis_id, id),
    FOREIGN KEY (owner_id, target_thesis_id, target_condition_id, kind)
        REFERENCES conditions(owner_id, thesis_id, id, kind),
    FOREIGN KEY (owner_id, accepted_thesis_id, accepted_version_id)
        REFERENCES thesis_versions(owner_id, thesis_id, id),
    CHECK ((target_thesis_id IS NULL AND base_version_id IS NULL
                AND kind = 'thesis' AND operation = 'ADD' AND target_condition_id IS NULL)
        OR (target_thesis_id IS NOT NULL AND base_version_id IS NOT NULL
                AND (kind <> 'thesis' OR operation <> 'ADD'))),
    CHECK ((kind = 'thesis' AND target_condition_id IS NULL)
        OR (kind <> 'thesis' AND ((operation = 'ADD' AND target_condition_id IS NULL)
            OR (operation IN ('UPDATE','REMOVE') AND target_condition_id IS NOT NULL)))),
    CHECK ((status = 'pending' AND resolved_at IS NULL)
        OR (status <> 'pending' AND resolved_at IS NOT NULL)),
    CHECK ((status = 'approved' AND accepted_thesis_id IS NOT NULL AND accepted_version_id IS NOT NULL)
        OR (status <> 'approved' AND accepted_thesis_id IS NULL AND accepted_version_id IS NULL))
);

CREATE TABLE alert_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL,
    thesis_id uuid NOT NULL,
    evaluation_id uuid NOT NULL,
    previous_evaluation_id uuid,
    event_kind text NOT NULL,
    dedup_key text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    read_at timestamptz,
    FOREIGN KEY (owner_id, thesis_id, evaluation_id) REFERENCES evaluations(owner_id, thesis_id, id),
    FOREIGN KEY (owner_id, thesis_id, previous_evaluation_id) REFERENCES evaluations(owner_id, thesis_id, id),
    UNIQUE (owner_id, id),
    UNIQUE (owner_id, dedup_key)
);
CREATE TABLE notification_channels (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES accounts(id),
    kind text NOT NULL CHECK (kind IN ('in_app','telegram','email')),
    destination_ref text NOT NULL,
    enabled boolean NOT NULL DEFAULT false,
    UNIQUE (owner_id, id),
    UNIQUE (owner_id, kind, destination_ref)
);
CREATE TABLE notification_deliveries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL,
    event_id uuid NOT NULL,
    channel_id uuid NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','sending','sent','failed','unknown')),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    provider_message_id text,
    last_attempt_at timestamptz,
    next_attempt_at timestamptz,
    FOREIGN KEY (owner_id, event_id) REFERENCES alert_events(owner_id, id),
    FOREIGN KEY (owner_id, channel_id) REFERENCES notification_channels(owner_id, id),
    UNIQUE (event_id, channel_id)
);

-- Internal worker-only accounting; no client role receives direct access.
CREATE TABLE model_calls (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid REFERENCES accounts(id),
    task_kind text NOT NULL,
    subject_ref text NOT NULL,
    idempotency_key text NOT NULL UNIQUE,
    provider text NOT NULL,
    model text NOT NULL,
    prompt_version text NOT NULL,
    input_fingerprint text NOT NULL,
    provider_request_id text,
    status text NOT NULL CHECK (status IN ('reserved','running','succeeded','failed','unknown')),
    reserved_usd numeric NOT NULL CHECK (reserved_usd >= 0),
    actual_usd numeric CHECK (actual_usd >= 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX owner_theses ON theses(owner_id, created_at DESC);
CREATE INDEX thesis_evaluations ON evaluations(owner_id, thesis_id, created_at DESC);
CREATE INDEX pending_proposals ON proposals(owner_id, created_at DESC) WHERE status = 'pending';
CREATE INDEX owner_alerts ON alert_events(owner_id, created_at DESC);
CREATE INDEX pending_deliveries ON notification_deliveries(next_attempt_at) WHERE status IN ('pending','failed');

-- The authenticated API supplies app.user_id with SET LOCAL inside each
-- transaction. Never accept it directly from a client or use a superuser API.
-- Missing tenant context returns no private rows. Production roles/grants,
-- worker authority and the existing authentication integration are separate.
DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'theses','thesis_versions','conditions','condition_versions',
        'thesis_version_conditions','evaluations','condition_results',
        'result_evidence','proposals','alert_events','notification_channels',
        'notification_deliveries'
    ] LOOP
        EXECUTE format('ALTER TABLE finance.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE finance.%I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format(
            'CREATE POLICY owner_only ON finance.%I USING (owner_id = nullif(current_setting(''app.user_id'', true), '''')::uuid) WITH CHECK (owner_id = nullif(current_setting(''app.user_id'', true), '''')::uuid)',
            table_name);
    END LOOP;
END $$;
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts FORCE ROW LEVEL SECURITY;
CREATE POLICY own_account ON accounts
    USING (id = nullif(current_setting('app.user_id', true), '')::uuid)
    WITH CHECK (id = nullif(current_setting('app.user_id', true), '')::uuid);
COMMIT;
