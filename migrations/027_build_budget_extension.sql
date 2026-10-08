-- Explicit owner decision on 2026-10-03: add US$10, for US$20 cumulative.
-- This does not reset or modify any existing call, charge, reservation or dispatch.
CREATE TABLE model_budget_amendments (
 authority text PRIMARY KEY,
 previous_cap_nano_usd bigint NOT NULL,
 approved_cap_nano_usd bigint NOT NULL,
 evidence text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER model_budget_amendments_immutable BEFORE UPDATE OR DELETE ON model_budget_amendments FOR EACH ROW EXECUTE FUNCTION immutable_record();
INSERT INTO model_budget_amendments(authority,previous_cap_nano_usd,approved_cap_nano_usd,evidence)
SELECT 'thesis-openai-build-20261003-usd20',cap_nano_usd,20000000000,
 'Owner: add 10 more dollars to the budget, so new budget is usd20; reported provider dashboard spending US$7.53 and authorized further testing. The dashboard total is not exact per-call reconciliation.'
FROM model_budget WHERE singleton;
ALTER TABLE model_budget DROP CONSTRAINT model_budget_cap_nano_usd_check;
ALTER TABLE model_budget ADD CONSTRAINT model_budget_cap_nano_usd_check CHECK(cap_nano_usd = 20000000000) NOT VALID;
UPDATE model_budget SET cap_nano_usd=20000000000,approval_reference='thesis-openai-build-20261003-usd20' WHERE singleton;
ALTER TABLE model_budget VALIDATE CONSTRAINT model_budget_cap_nano_usd_check;
GRANT SELECT ON model_budget_amendments TO thesis_app;
