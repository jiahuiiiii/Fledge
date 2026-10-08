-- Public source samples, shared interpretation, private watch/review state.
CREATE TABLE social_feeds(feed text PRIMARY KEY,enabled boolean NOT NULL DEFAULT true);
INSERT INTO social_feeds(feed) VALUES('stocks'),('investing'),('wallstreetbets');
CREATE TABLE social_posts(id uuid PRIMARY KEY,instrument_id uuid NOT NULL REFERENCES instruments,
 platform text NOT NULL CHECK(platform='reddit'),feed text NOT NULL REFERENCES social_feeds,
 post_key text NOT NULL,author_hash text,content_hash text NOT NULL,title text NOT NULL,body text NOT NULL,
 url text NOT NULL,published_at timestamptz NOT NULL,available_at timestamptz NOT NULL,
 UNIQUE(instrument_id,post_key,content_hash),CHECK(available_at>=published_at));
CREATE TABLE social_refresh_state(feed text PRIMARY KEY REFERENCES social_feeds,last_attempt_at timestamptz,
 completed_at timestamptz,post_count integer,matched_count integer,excluded_count integer,error text);
CREATE TABLE social_refresh_lock(singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),attempt_id uuid,lease_until timestamptz,last_attempt_at timestamptz);
INSERT INTO social_refresh_lock(singleton) VALUES(true);
CREATE TABLE sentiment_analyses(id uuid PRIMARY KEY,instrument_id uuid NOT NULL REFERENCES instruments,
 request_key text NOT NULL UNIQUE,call_id uuid NOT NULL REFERENCES model_calls,
 packet jsonb NOT NULL,result jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX sentiment_latest ON sentiment_analyses(instrument_id,created_at DESC);
ALTER TABLE sentiment_analyses ADD UNIQUE(instrument_id,id);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON social_posts FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON sentiment_analyses FOR EACH ROW EXECUTE FUNCTION immutable_record();
GRANT SELECT ON social_feeds,social_posts,social_refresh_state,social_refresh_lock,sentiment_analyses TO thesis_app;
GRANT SELECT,INSERT ON social_posts,social_refresh_state TO thesis_source;
GRANT SELECT ON social_feeds TO thesis_source;
GRANT UPDATE ON social_refresh_state TO thesis_source;
GRANT SELECT,UPDATE ON social_refresh_lock TO thesis_source;
GRANT INSERT ON sentiment_analyses TO thesis_app;
CREATE TABLE news_watches(owner_id uuid NOT NULL REFERENCES accounts,instrument_id uuid NOT NULL REFERENCES instruments,
 enabled boolean NOT NULL DEFAULT false,interval_minutes integer NOT NULL DEFAULT 60 CHECK(interval_minutes IN (60,240)),
 next_check_at timestamptz,last_check_at timestamptz,lease_until timestamptz,claim_token uuid,
 baseline_id uuid,error text,PRIMARY KEY(owner_id,instrument_id),
 FOREIGN KEY(instrument_id,baseline_id) REFERENCES sentiment_analyses(instrument_id,id));
CREATE TABLE watch_seen_sources(owner_id uuid NOT NULL,instrument_id uuid NOT NULL,
 channel text NOT NULL CHECK(channel IN ('news','social')),content_hash text NOT NULL,
 first_seen_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(owner_id,instrument_id,channel,content_hash),
 FOREIGN KEY(owner_id,instrument_id) REFERENCES news_watches(owner_id,instrument_id));
CREATE TABLE research_alerts(id uuid PRIMARY KEY,owner_id uuid NOT NULL REFERENCES accounts,instrument_id uuid NOT NULL REFERENCES instruments,
 kind text NOT NULL CHECK(kind IN ('sentiment','new_reporting')),current_id uuid NOT NULL REFERENCES sentiment_analyses,
 previous_id uuid NOT NULL REFERENCES sentiment_analyses,version_id uuid,
 payload jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(owner_id,instrument_id,current_id,kind),
 UNIQUE(owner_id,id),FOREIGN KEY(owner_id,version_id) REFERENCES thesis_versions(owner_id,id),
 FOREIGN KEY(instrument_id,current_id) REFERENCES sentiment_analyses(instrument_id,id),
 FOREIGN KEY(instrument_id,previous_id) REFERENCES sentiment_analyses(instrument_id,id));
CREATE TABLE research_alert_reviews(owner_id uuid NOT NULL,alert_id uuid NOT NULL,action text NOT NULL CHECK(action IN ('reviewed','unresolved')),
 created_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(owner_id,alert_id),FOREIGN KEY(owner_id,alert_id) REFERENCES research_alerts(owner_id,id));
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['news_watches','watch_seen_sources','research_alerts','research_alert_reviews'] LOOP
 EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY account_scope ON %I USING(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
 EXECUTE format('GRANT SELECT,INSERT ON %I TO thesis_app',t);
 IF t<>'news_watches' THEN EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION immutable_record()',t); END IF;
 END LOOP;
END $$;
GRANT UPDATE ON news_watches TO thesis_app;
