-- Company-directed Deus discovery; source text and prior labels remain immutable.
CREATE TABLE reddit_company_checks (
 instrument_id uuid PRIMARY KEY REFERENCES instruments, attempt_id uuid, lease_until timestamptz,
 last_attempt_at timestamptz, completed_at timestamptz, lookback_days integer,
 post_count integer, matched_count integer, excluded_count integer, error text
);
CREATE TABLE reddit_request_clock (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), next_at timestamptz NOT NULL,
 blocked_until timestamptz, reason text
);
INSERT INTO reddit_request_clock VALUES(true,now(),NULL,NULL);
CREATE TABLE social_discovery (
 post_id uuid PRIMARY KEY REFERENCES social_posts,
 thread_key text NOT NULL, kind text NOT NULL CHECK(kind IN ('post','comment')),
 match_basis text NOT NULL CHECK(match_basis IN ('direct','thread')),
 method text NOT NULL
);
CREATE TABLE social_withdrawals(post_key text PRIMARY KEY,checked_at timestamptz NOT NULL);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON social_discovery FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON social_withdrawals FOR EACH ROW EXECUTE FUNCTION immutable_record();
GRANT SELECT ON reddit_company_checks,reddit_request_clock,social_discovery,social_withdrawals TO thesis_app;
GRANT SELECT,INSERT,UPDATE ON reddit_company_checks TO thesis_source;
GRANT SELECT,UPDATE ON reddit_request_clock TO thesis_source;
GRANT SELECT,INSERT ON social_discovery,social_withdrawals TO thesis_source;
