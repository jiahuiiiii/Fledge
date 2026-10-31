-- Saved arrangement of the overview and home widgets, per account, page and
-- screen width. Presentation only: no research, prices or saved reasoning.
-- Widget ids are checked against the server's allow-list on save and read;
-- unknown ids are dropped on read so renamed widgets never break a layout.
-- Owner approved 31 October 2026 (draggable workspace plan, Feature A).
CREATE TABLE workspace_layouts (
 owner_id uuid NOT NULL REFERENCES accounts ON DELETE CASCADE,
 page text NOT NULL CHECK(page IN ('overview','home')),
 breakpoint text NOT NULL CHECK(breakpoint IN ('lg','md','sm')),
 layout jsonb NOT NULL CHECK(jsonb_typeof(layout)='array'),
 hidden jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(hidden)='array'),
 updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(owner_id,page,breakpoint)
);
ALTER TABLE workspace_layouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_layouts FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON workspace_layouts
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT,UPDATE,DELETE ON workspace_layouts TO thesis_app;
