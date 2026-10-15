-- Investor-type quiz: two more first-login answers (optional for older profiles).
ALTER TABLE investor_profiles
 ADD COLUMN trade_frequency text CHECK(trade_frequency IN ('daily','weekly','monthly','rarely','unsure')),
 ADD COLUMN drop_reaction text CHECK(drop_reaction IN ('sell','hold','add','check','unsure'));

-- PDPA: a record of which Terms of Use and Privacy Notice version each account
-- accepted, and when. Rows are never updated; a new version adds a new row.
CREATE TABLE terms_acceptances (
 account_id uuid NOT NULL REFERENCES accounts ON DELETE CASCADE,
 terms_version text NOT NULL CHECK(terms_version ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'),
 accepted_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(account_id, terms_version)
);
ALTER TABLE terms_acceptances ENABLE ROW LEVEL SECURITY;
ALTER TABLE terms_acceptances FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON terms_acceptances
 USING(account_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(account_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT ON terms_acceptances TO thesis_app;
