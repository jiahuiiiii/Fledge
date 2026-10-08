CREATE UNIQUE INDEX model_calls_owner_identity ON model_calls(owner_id,id);
CREATE TABLE research_answers (
 id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES accounts,
 instrument_id uuid NOT NULL REFERENCES instruments,
 parent_id uuid, call_id uuid,
 request_key text NOT NULL, question text NOT NULL CHECK(length(question) BETWEEN 3 AND 600),
 packet jsonb NOT NULL, result jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id,request_key), UNIQUE(owner_id,instrument_id,id),
 FOREIGN KEY(owner_id,instrument_id,parent_id) REFERENCES research_answers(owner_id,instrument_id,id),
 FOREIGN KEY(owner_id,call_id) REFERENCES model_calls(owner_id,id)
);
ALTER TABLE research_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_answers FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON research_answers
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT ON research_answers TO thesis_app;
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON research_answers FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE INDEX research_answers_history ON research_answers(owner_id,instrument_id,created_at DESC,id DESC);
