-- Owner instruction on 2026-10-05: increase the cumulative test allowance to US$30.
-- Retain all existing charges, holds, accounting decisions and dispatch records.
INSERT INTO model_budget_amendments(authority,previous_cap_nano_usd,approved_cap_nano_usd,evidence)
SELECT 'thesis-openai-build-20261005-usd30',cap_nano_usd,30000000000,
 'Owner: If you need to use the api credit to test just, i increase the budget to US$30. UI/UX improvements first, then valuation and alternative data sources.'
FROM model_budget WHERE singleton;
ALTER TABLE model_budget DROP CONSTRAINT model_budget_cap_nano_usd_check;
ALTER TABLE model_budget ADD CONSTRAINT model_budget_cap_nano_usd_check CHECK(cap_nano_usd = 30000000000) NOT VALID;
UPDATE model_budget SET cap_nano_usd=30000000000,approval_reference='thesis-openai-build-20261005-usd30' WHERE singleton;
ALTER TABLE model_budget VALIDATE CONSTRAINT model_budget_cap_nano_usd_check;
