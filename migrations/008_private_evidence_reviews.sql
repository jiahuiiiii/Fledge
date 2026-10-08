-- A correction may return to earlier article content. Its occurrence and
-- supersession chain are new even when the content hash has been seen before.
ALTER TABLE document_versions DROP CONSTRAINT document_versions_document_id_content_hash_key;
CREATE INDEX document_versions_latest ON document_versions(document_id,available_at DESC,id DESC);

-- The shared spending total is visible, but private prompts and responses are
-- scoped to their owner just like saved reasoning. Existing shared calls stay shared.
ALTER TABLE model_calls ADD COLUMN owner_id uuid REFERENCES accounts(id);
ALTER TABLE model_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_calls FORCE ROW LEVEL SECURITY;
CREATE POLICY model_call_scope ON model_calls USING(owner_id IS NULL OR owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id IS NULL OR owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
ALTER TABLE model_dispatches ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_dispatches FORCE ROW LEVEL SECURITY;
CREATE POLICY model_dispatch_scope ON model_dispatches USING(EXISTS(SELECT 1 FROM model_calls c WHERE c.id=call_id))
 WITH CHECK(EXISTS(SELECT 1 FROM model_calls c WHERE c.id=call_id));
CREATE FUNCTION model_global_totals() RETURNS TABLE(spent bigint,held bigint,calls bigint,unresolved bigint)
 LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT coalesce(sum(charged_nano_usd),0)::bigint,
 coalesce(sum(reserved_nano_usd) FILTER(WHERE status<>'settled'),0)::bigint,
 count(*),count(*) FILTER(WHERE status<>'settled') FROM public.model_calls
 $$;
REVOKE ALL ON FUNCTION model_global_totals() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION model_global_totals() TO thesis_app;

CREATE TABLE idea_evidence_reviews (
  id uuid PRIMARY KEY,
  owner_id uuid NOT NULL REFERENCES accounts(id),
  version_id uuid NOT NULL,
  evaluation_id uuid,
  snapshot_id bigint NOT NULL REFERENCES research_snapshots(id),
  call_id uuid NOT NULL REFERENCES model_calls(id),
  request_key text NOT NULL,
  packet jsonb NOT NULL,
  result jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY(owner_id,version_id) REFERENCES thesis_versions(owner_id,id),
  FOREIGN KEY(owner_id,evaluation_id,version_id) REFERENCES evaluations(owner_id,id,version_id),
  UNIQUE(owner_id,request_key)
);
ALTER TABLE idea_evidence_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE idea_evidence_reviews FORCE ROW LEVEL SECURITY;
CREATE POLICY private_evidence_review ON idea_evidence_reviews USING (owner_id=nullif(current_setting('app.user_id',true),'')::uuid) WITH CHECK (owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT ON idea_evidence_reviews TO thesis_app;
CREATE TRIGGER idea_evidence_reviews_immutable BEFORE UPDATE OR DELETE ON idea_evidence_reviews FOR EACH ROW EXECUTE FUNCTION immutable_record();
