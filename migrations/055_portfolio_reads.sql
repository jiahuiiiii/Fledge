-- Your list today: the optional AI explanation of the whole watchlist.
-- Private to each account; the plain read is built from existing tables.
CREATE TABLE portfolio_reads (
 id uuid PRIMARY KEY,
 owner_id uuid NOT NULL REFERENCES accounts ON DELETE CASCADE,
 call_id uuid NOT NULL REFERENCES model_calls,
 created_at timestamptz NOT NULL,
 company_ids uuid[] NOT NULL,
 result jsonb NOT NULL
);
CREATE INDEX portfolio_read_latest ON portfolio_reads(owner_id,created_at DESC);
ALTER TABLE portfolio_reads ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_reads FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON portfolio_reads
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT ON portfolio_reads TO thesis_app;
