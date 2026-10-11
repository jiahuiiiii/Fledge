-- First-login answers and a per-account watchlist of at most five companies.
-- Answers tailor explanations and the home page only; they never choose,
-- rank or recommend investments.
CREATE TABLE investor_profiles (
 owner_id uuid PRIMARY KEY REFERENCES accounts ON DELETE CASCADE,
 experience text NOT NULL CHECK(experience IN ('new','etf','stocks','active')),
 interests text[] NOT NULL DEFAULT '{}' CHECK(cardinality(interests)<=9),
 horizon text NOT NULL CHECK(horizon IN ('short','medium','long','unsure')),
 goal text NOT NULL CHECK(goal IN ('learn','check','monitor')),
 detail_mode text NOT NULL CHECK(detail_mode IN ('explain','data')),
 completed_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE investor_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE investor_profiles FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON investor_profiles
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT,UPDATE ON investor_profiles TO thesis_app;

CREATE TABLE watchlist_companies (
 owner_id uuid NOT NULL REFERENCES accounts ON DELETE CASCADE,
 instrument_id uuid NOT NULL REFERENCES instruments ON DELETE CASCADE,
 added_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(owner_id,instrument_id)
);
ALTER TABLE watchlist_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist_companies FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON watchlist_companies
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT,DELETE ON watchlist_companies TO thesis_app;

-- The limit is enforced in the database so concurrent requests cannot exceed it.
CREATE FUNCTION enforce_watchlist_limit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended('watchlist:'||NEW.owner_id::text,0));
 IF EXISTS(SELECT 1 FROM watchlist_companies WHERE owner_id=NEW.owner_id AND instrument_id=NEW.instrument_id) THEN
  RETURN NEW; -- already listed; ON CONFLICT leaves it unchanged
 END IF;
 IF (SELECT count(*) FROM watchlist_companies WHERE owner_id=NEW.owner_id)>=5 THEN
  RAISE EXCEPTION 'watchlist_limit' USING ERRCODE='check_violation';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER watchlist_limit BEFORE INSERT ON watchlist_companies
 FOR EACH ROW EXECUTE FUNCTION enforce_watchlist_limit();
