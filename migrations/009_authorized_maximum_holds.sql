-- An explicit owner accounting decision may permit new work while retaining an
-- interrupted call's full maximum. This is not a fabricated settled charge.
-- Ordinary application/source roles cannot create or alter these decisions.
CREATE TABLE model_accounting_decisions (
 call_id uuid PRIMARY KEY REFERENCES model_calls(id),
 authority text NOT NULL CHECK(length(authority)>0),
 evidence text NOT NULL CHECK(length(evidence)>0),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER model_accounting_decisions_immutable BEFORE UPDATE OR DELETE ON model_accounting_decisions FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE FUNCTION validate_maximum_hold() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM model_calls c JOIN model_dispatches d ON d.call_id=c.id WHERE c.id=NEW.call_id AND c.status='unresolved')
 THEN RAISE EXCEPTION 'Only an unresolved dispatched call can retain an authorized maximum hold'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER validate_maximum_hold BEFORE INSERT ON model_accounting_decisions FOR EACH ROW EXECUTE FUNCTION validate_maximum_hold();
CREATE OR REPLACE FUNCTION model_global_totals() RETURNS TABLE(spent bigint,held bigint,calls bigint,unresolved bigint)
 LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(sum(c.charged_nano_usd),0)::bigint,
 coalesce(sum(c.reserved_nano_usd) FILTER(WHERE c.status<>'settled'),0)::bigint,
 count(*),count(*) FILTER(WHERE c.status<>'settled' AND d.call_id IS NULL)
 FROM public.model_calls c LEFT JOIN public.model_accounting_decisions d ON d.call_id=c.id
 $$;
CREATE FUNCTION model_accounted_maximum() RETURNS bigint
 LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(sum(c.reserved_nano_usd),0)::bigint FROM public.model_calls c
 JOIN public.model_accounting_decisions d ON d.call_id=c.id WHERE c.status<>'settled'
 $$;
REVOKE ALL ON FUNCTION model_accounted_maximum() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION model_accounted_maximum() TO thesis_app;
