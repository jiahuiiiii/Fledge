-- One cumulative allowance for all model work in this Thesis installation.
CREATE TABLE model_budget (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 approval_reference text NOT NULL,
 cap_nano_usd bigint NOT NULL CHECK(cap_nano_usd = 10000000000),
 created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO model_budget(singleton,approval_reference,cap_nano_usd)
VALUES(true,'thesis-openai-build-20261001-usd10',10000000000);
CREATE TABLE model_calls (
 id uuid PRIMARY KEY,
 request_key text UNIQUE NOT NULL,
 request_hash text NOT NULL,
 purpose text NOT NULL,
 model text NOT NULL,
 price_version text NOT NULL,
 request_body jsonb NOT NULL,
 reserved_nano_usd bigint NOT NULL CHECK(reserved_nano_usd > 0),
 status text NOT NULL CHECK(status IN ('dispatched','settled','unresolved')),
 response_id text,
 response_body jsonb,
 input_tokens integer,
 cached_tokens integer,
 output_tokens integer,
 charged_nano_usd bigint CHECK(charged_nano_usd >= 0),
 error_code text,
 created_at timestamptz NOT NULL DEFAULT now(),
 finished_at timestamptz,
 CHECK((status='settled') = (charged_nano_usd IS NOT NULL))
);
GRANT SELECT ON model_budget,model_calls TO thesis_app;
GRANT INSERT ON model_calls TO thesis_app;
GRANT UPDATE(status,response_id,response_body,input_tokens,cached_tokens,output_tokens,charged_nano_usd,error_code,finished_at) ON model_calls TO thesis_app;
-- App roles cannot reset the allowance or delete previous charges.

CREATE FUNCTION freeze_model_charge() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.status='settled' THEN RAISE EXCEPTION 'Settled provider charges are immutable'; END IF;
 IF NEW.status NOT IN ('unresolved','settled') THEN RAISE EXCEPTION 'Provider calls cannot be dispatched again'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER preserve_model_charge BEFORE UPDATE ON model_calls FOR EACH ROW EXECUTE FUNCTION freeze_model_charge();
CREATE TABLE model_dispatches(call_id uuid PRIMARY KEY REFERENCES model_calls, started_at timestamptz NOT NULL DEFAULT now());
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON model_dispatches FOR EACH ROW EXECUTE FUNCTION immutable_record();
GRANT SELECT,INSERT ON model_dispatches TO thesis_app;
