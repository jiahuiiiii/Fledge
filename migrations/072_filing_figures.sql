-- A company's finished filing figures (financial_depth.present), saved per
-- account and per exact set of inputs so they are rebuilt only when an input
-- changes, not on every request or restart. `basis` hashes every input:
-- source access, the SEC payload version, every saved disclosure document,
-- this account's reviewed recoveries and the calculation versions.
-- Account-scoped like financial_recovery_readings, because reviewed
-- recoveries are private to an account. Append-only. Approved by the owner
-- on 25 October 2026 (saved-filing-figures-design.md).
CREATE TABLE filing_figures (
 owner_id uuid NOT NULL REFERENCES accounts,
 instrument_id uuid NOT NULL REFERENCES instruments,
 basis text NOT NULL,
 depth jsonb NOT NULL,
 computed_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(owner_id, instrument_id, basis)
);
ALTER TABLE filing_figures ENABLE ROW LEVEL SECURITY;
ALTER TABLE filing_figures FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON filing_figures
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON filing_figures
 FOR EACH ROW EXECUTE FUNCTION immutable_record();
GRANT SELECT,INSERT ON filing_figures TO thesis_app;
