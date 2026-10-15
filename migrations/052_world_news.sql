-- World news: Finnhub general market headlines shared by every account, plus
-- each account's private AI check of which watchlist companies they might touch.
CREATE TABLE world_news_articles (
 id uuid PRIMARY KEY,
 url text NOT NULL UNIQUE CHECK(url ~ '^https?://'),
 headline text NOT NULL CHECK(length(headline) BETWEEN 1 AND 600),
 summary text NOT NULL DEFAULT '' CHECK(length(summary)<=6000),
 publisher text NOT NULL CHECK(length(publisher) BETWEEN 1 AND 180),
 category text NOT NULL,
 provider_id text NOT NULL DEFAULT '',
 published_at timestamptz NOT NULL,
 retrieved_at timestamptz NOT NULL,
 themes text[] NOT NULL DEFAULT '{}'
);
CREATE INDEX world_news_recent ON world_news_articles(published_at DESC);
CREATE TABLE world_news_state (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 attempted_at timestamptz,
 checked_at timestamptz,
 error text,
 rejected integer NOT NULL DEFAULT 0 CHECK(rejected>=0)
);
INSERT INTO world_news_state(singleton) VALUES(true);
GRANT SELECT ON world_news_articles,world_news_state TO thesis_app;
GRANT SELECT,INSERT,UPDATE ON world_news_articles,world_news_state TO thesis_source;

CREATE TABLE world_news_checks (
 id uuid PRIMARY KEY,
 owner_id uuid NOT NULL REFERENCES accounts ON DELETE CASCADE,
 call_id uuid NOT NULL REFERENCES model_calls,
 checked_at timestamptz NOT NULL,
 article_ids uuid[] NOT NULL,
 companies jsonb NOT NULL,
 links jsonb NOT NULL,
 dropped integer NOT NULL DEFAULT 0 CHECK(dropped>=0)
);
CREATE INDEX world_news_check_latest ON world_news_checks(owner_id,checked_at DESC);
ALTER TABLE world_news_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE world_news_checks FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON world_news_checks
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT ON world_news_checks TO thesis_app;
