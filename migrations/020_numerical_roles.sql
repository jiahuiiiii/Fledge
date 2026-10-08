-- Existing numerical definitions remain requirements. Historical results/manifests stay intact.
ALTER TABLE version_conditions ADD COLUMN role text NOT NULL DEFAULT 'required'
 CHECK(role IN ('required','risk'));
