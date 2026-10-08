ALTER TABLE sources DROP CONSTRAINT sources_entitlement_check;
ALTER TABLE sources ADD CONSTRAINT sources_entitlement_check CHECK(entitlement IN ('fictional','sec-public','finnhub-pitch','public-news','local-yahoo-history','local-stockanalysis-targets'));
ALTER TABLE social_posts DROP CONSTRAINT social_posts_platform_check;
ALTER TABLE social_posts ADD CONSTRAINT social_posts_platform_check CHECK(platform IN ('reddit','hackernews','x'));
INSERT INTO social_feeds(feed) VALUES('x');

CREATE TABLE provider_checks (
 instrument_id uuid NOT NULL REFERENCES instruments, provider text NOT NULL,
 attempt_id uuid, lease_until timestamptz, last_attempt_at timestamptz,
 completed_at timestamptz, outcome text, message text, fetched integer DEFAULT 0,
 matched integer DEFAULT 0, PRIMARY KEY(instrument_id,provider)
);
CREATE TABLE provider_clocks (
 provider text PRIMARY KEY, next_at timestamptz NOT NULL DEFAULT '1970-01-01T00:00:00Z',
 blocked_until timestamptz, denied boolean NOT NULL DEFAULT false,
 usage_date date NOT NULL DEFAULT CURRENT_DATE, requests integer NOT NULL DEFAULT 0
);
CREATE TABLE public_feed_cache (
 provider text PRIMARY KEY, body bytea NOT NULL, retrieved_at timestamptz NOT NULL
);
GRANT SELECT ON provider_checks,provider_clocks TO thesis_app;
GRANT SELECT,INSERT,UPDATE ON provider_checks,provider_clocks,public_feed_cache TO thesis_source;
