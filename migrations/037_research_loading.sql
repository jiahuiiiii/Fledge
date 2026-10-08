-- Visible, durable acquisition queue. Starting a load never enables a watch.
CREATE TABLE research_loads (
 id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES accounts,
 instrument_id uuid NOT NULL REFERENCES instruments,
 lookback_days integer NOT NULL CHECK(lookback_days IN (1,7,30)),
 steps jsonb NOT NULL, active boolean NOT NULL DEFAULT true,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX one_active_research_load ON research_loads(owner_id,instrument_id) WHERE active;
ALTER TABLE research_loads ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_loads FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON research_loads USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid) WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT,UPDATE ON research_loads TO thesis_app;
-- Aggregate state only: never expose another owner's prompts or research.
CREATE FUNCTION model_activity() RETURNS TABLE(running bigint,needs_attention bigint)
 LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT count(*) FILTER(WHERE c.status='dispatched' AND c.created_at>now()-interval '15 minutes'),
 count(*) FILTER(WHERE c.status='unresolved' OR (c.status='dispatched' AND c.created_at<=now()-interval '15 minutes'))
 FROM public.model_calls c LEFT JOIN public.model_accounting_decisions d ON d.call_id=c.id
 WHERE c.status<>'settled' AND d.call_id IS NULL
 $$;
REVOKE ALL ON FUNCTION model_activity() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION model_activity() TO thesis_app;
