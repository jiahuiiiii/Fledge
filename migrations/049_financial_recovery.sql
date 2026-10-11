-- Optional owner-reviewed interpretations of public filing cells. Original
-- source payloads and numerical monitoring observations are never rewritten.
CREATE TABLE financial_recovery_readings (
 id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES accounts,
 instrument_id uuid NOT NULL REFERENCES instruments,
 document_id uuid NOT NULL, request_key text NOT NULL,
 call_id uuid NOT NULL REFERENCES model_calls,
 packet jsonb NOT NULL, result jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id,request_key), UNIQUE(id,owner_id),
 FOREIGN KEY(document_id,instrument_id) REFERENCES disclosure_documents(id,instrument_id)
);
CREATE TABLE financial_recovery_reviews (
 id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES accounts,
 reading_id uuid NOT NULL, accepted jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(reading_id,owner_id) REFERENCES financial_recovery_readings(id,owner_id)
);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['financial_recovery_readings','financial_recovery_reviews'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('CREATE POLICY account_scope ON %I USING(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
  EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION immutable_record()',t);
  EXECUTE format('GRANT SELECT,INSERT ON %I TO thesis_app',t);
 END LOOP;
END $$;
CREATE INDEX financial_recovery_history ON financial_recovery_readings(owner_id,instrument_id,created_at DESC,id DESC);
CREATE INDEX financial_recovery_review_history ON financial_recovery_reviews(reading_id,created_at DESC,id DESC);
