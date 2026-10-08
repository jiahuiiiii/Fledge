-- Private questions are research bookmarks, not saved idea revisions or watches.
CREATE TABLE research_question_library (
 id uuid PRIMARY KEY,
 owner_id uuid NOT NULL REFERENCES accounts ON DELETE CASCADE,
 instrument_id uuid NOT NULL REFERENCES instruments ON DELETE CASCADE,
 question text NOT NULL CHECK(length(question) BETWEEN 3 AND 600),
 question_key text NOT NULL,
 selected boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id,instrument_id,question_key)
);
CREATE UNIQUE INDEX one_selected_research_question
 ON research_question_library(owner_id,instrument_id) WHERE selected;
ALTER TABLE research_question_library ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_question_library FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON research_question_library
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT,UPDATE ON research_question_library TO thesis_app;
