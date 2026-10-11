-- Owner instruction on 2026-10-11: increase the cumulative test allowance to US$40.
-- Retain all existing charges, holds, accounting decisions and dispatch records.
INSERT INTO model_budget_amendments(authority,previous_cap_nano_usd,approved_cap_nano_usd,evidence)
SELECT 'thesis-openai-build-20261011-usd40',cap_nano_usd,40000000000,
 'Owner chose "Raise cap to US$40" when the Qualcomm Refresh & analyse needed up to US$3.25 reserved with US$2.04 remaining.'
FROM model_budget WHERE singleton;
ALTER TABLE model_budget DROP CONSTRAINT model_budget_cap_nano_usd_check;
ALTER TABLE model_budget ADD CONSTRAINT model_budget_cap_nano_usd_check CHECK(cap_nano_usd = 40000000000) NOT VALID;
UPDATE model_budget SET cap_nano_usd=40000000000,approval_reference='thesis-openai-build-20261011-usd40' WHERE singleton;
ALTER TABLE model_budget VALIDATE CONSTRAINT model_budget_cap_nano_usd_check;
