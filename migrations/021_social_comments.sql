-- Additional public discussion samples; existing Reddit records remain immutable.
ALTER TABLE social_posts DROP CONSTRAINT social_posts_platform_check;
ALTER TABLE social_posts ADD CONSTRAINT social_posts_platform_check CHECK(platform IN ('reddit','hackernews'));
INSERT INTO social_feeds(feed) VALUES('hackernews');
CREATE TABLE hn_refresh_state(instrument_id uuid PRIMARY KEY REFERENCES instruments,
 attempt_id uuid,lease_until timestamptz,last_attempt_at timestamptz,completed_at timestamptz,
 post_count integer,matched_count integer,excluded_count integer,error text);
CREATE TABLE hn_withdrawals(post_key text PRIMARY KEY,checked_at timestamptz NOT NULL);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON hn_withdrawals FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TABLE hn_request_clock(singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),next_at timestamptz NOT NULL);
INSERT INTO hn_request_clock VALUES(true,now());
GRANT SELECT ON hn_refresh_state,hn_withdrawals TO thesis_app;
GRANT SELECT,INSERT,UPDATE ON hn_refresh_state TO thesis_source;
GRANT SELECT,INSERT ON hn_withdrawals TO thesis_source;
GRANT SELECT,UPDATE ON hn_request_clock TO thesis_source;
