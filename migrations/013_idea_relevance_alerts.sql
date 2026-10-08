-- Private source-to-reasoning checks; company research remains shared.
ALTER TABLE news_watches ADD COLUMN match_idea boolean NOT NULL DEFAULT false;
CREATE TABLE idea_watch_state(owner_id uuid NOT NULL REFERENCES accounts,instrument_id uuid NOT NULL REFERENCES instruments,
 version_id uuid NOT NULL,baseline_id uuid NOT NULL,last_check_at timestamptz NOT NULL DEFAULT now(),status text NOT NULL CHECK(status IN ('baseline','quiet','checked')),
 PRIMARY KEY(owner_id,instrument_id),FOREIGN KEY(owner_id,version_id) REFERENCES thesis_versions(owner_id,id),
 FOREIGN KEY(instrument_id,baseline_id) REFERENCES sentiment_analyses(instrument_id,id));
CREATE TABLE idea_watch_seen(owner_id uuid NOT NULL,version_id uuid NOT NULL,channel text NOT NULL CHECK(channel IN ('news','social')),content_key text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(owner_id,version_id,channel,content_key),
 FOREIGN KEY(owner_id,version_id) REFERENCES thesis_versions(owner_id,id));
CREATE TABLE idea_alert_checks(id uuid PRIMARY KEY,owner_id uuid NOT NULL REFERENCES accounts,instrument_id uuid NOT NULL REFERENCES instruments,
 version_id uuid NOT NULL,analysis_id uuid NOT NULL,call_id uuid NOT NULL REFERENCES model_calls,request_key text NOT NULL,packet jsonb NOT NULL,result jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(owner_id,id),UNIQUE(owner_id,request_key),
 FOREIGN KEY(owner_id,version_id) REFERENCES thesis_versions(owner_id,id),
 FOREIGN KEY(instrument_id,analysis_id) REFERENCES sentiment_analyses(instrument_id,id));
CREATE TABLE idea_alert_publications(owner_id uuid NOT NULL,check_id uuid NOT NULL,mode text NOT NULL CHECK(mode IN ('manual','watch')),
 created_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(owner_id,check_id),
 FOREIGN KEY(owner_id,check_id) REFERENCES idea_alert_checks(owner_id,id));
CREATE TABLE idea_alert_reviews(owner_id uuid NOT NULL,check_id uuid NOT NULL,action text NOT NULL CHECK(action IN ('reviewed','unresolved')),
 created_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(owner_id,check_id),
 FOREIGN KEY(owner_id,check_id) REFERENCES idea_alert_checks(owner_id,id));
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['idea_watch_state','idea_watch_seen','idea_alert_checks','idea_alert_publications','idea_alert_reviews'] LOOP
 EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY account_scope ON %I USING(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid) WITH CHECK(owner_id=nullif(current_setting(''app.user_id'',true),'''')::uuid)',t);
 EXECUTE format('GRANT SELECT,INSERT ON %I TO thesis_app',t);
 IF t<>'idea_watch_state' THEN EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION immutable_record()',t); END IF;
 END LOOP;
END $$;
GRANT UPDATE ON idea_watch_state TO thesis_app;
CREATE FUNCTION idea_alert_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM thesis_versions v JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id
 WHERE v.id=NEW.version_id AND v.owner_id=NEW.owner_id AND t.instrument_id=NEW.instrument_id) THEN
 RAISE EXCEPTION 'Saved reasoning does not match this owner and company'; END IF;
 IF TG_TABLE_NAME='idea_alert_checks' THEN
  IF NOT EXISTS(SELECT 1 FROM model_calls WHERE id=NEW.call_id AND owner_id=NEW.owner_id) THEN
   RAISE EXCEPTION 'Private check requires a matching private model call';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER check_membership BEFORE INSERT ON idea_alert_checks FOR EACH ROW EXECUTE FUNCTION idea_alert_membership();
CREATE TRIGGER state_membership BEFORE INSERT OR UPDATE ON idea_watch_state FOR EACH ROW EXECUTE FUNCTION idea_alert_membership();
