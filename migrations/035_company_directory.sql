-- Public SEC identity cache; refresh pacing persists across app restarts.
CREATE TABLE company_directory (
 singleton boolean PRIMARY KEY CHECK(singleton),
 listings jsonb NOT NULL DEFAULT '[]', retrieved_at timestamptz,
 attempted_at timestamptz, attempt_id uuid, lease_until timestamptz, error text
);
INSERT INTO company_directory(singleton) VALUES(true);
GRANT SELECT ON company_directory TO thesis_app;
GRANT SELECT,UPDATE ON company_directory TO thesis_source;
CREATE TABLE workspace_settings (
 singleton boolean PRIMARY KEY CHECK(singleton),
 seed_demo boolean NOT NULL DEFAULT true,
 reset_at timestamptz
);
INSERT INTO workspace_settings(singleton) VALUES(true);
GRANT SELECT ON workspace_settings TO thesis_app;
