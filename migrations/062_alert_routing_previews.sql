-- Additive shadow routing; existing alerts remain ordinary saved publications.
ALTER TABLE research_alerts ADD COLUMN preview boolean NOT NULL DEFAULT false;
ALTER TABLE research_alerts DROP CONSTRAINT research_alerts_kind_check;
ALTER TABLE research_alerts ADD CHECK(kind IN ('sentiment','new_reporting','important_reporting'));
ALTER TABLE research_alerts ADD CHECK(kind<>'important_reporting' OR preview);

CREATE TABLE alert_routing_decisions (
 id uuid PRIMARY KEY,owner_id uuid NOT NULL REFERENCES accounts,
 kind text NOT NULL CHECK(kind IN ('company','idea','condition','move')),
 event_id uuid NOT NULL,policy text NOT NULL,
 severity text NOT NULL CHECK(severity IN ('high','medium','low')),
 channel text NOT NULL CHECK(channel IN ('telegram','digest','app')),
 preview boolean NOT NULL DEFAULT true CHECK(preview),
 reason text NOT NULL,manifest jsonb NOT NULL,created_at timestamptz NOT NULL,
 UNIQUE(owner_id,kind,event_id,policy),
 CHECK((severity,channel) IN (('high','telegram'),('medium','digest'),('low','app')))
);
CREATE INDEX routing_by_channel ON alert_routing_decisions(owner_id,channel,created_at,id);
ALTER TABLE alert_routing_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_routing_decisions FORCE ROW LEVEL SECURITY;
CREATE POLICY account_scope ON alert_routing_decisions
 USING(owner_id=nullif(current_setting('app.user_id',true),'')::uuid)
 WITH CHECK(owner_id=nullif(current_setting('app.user_id',true),'')::uuid);
GRANT SELECT,INSERT ON alert_routing_decisions TO thesis_app;
CREATE TRIGGER check_membership BEFORE INSERT ON alert_routing_decisions
 FOR EACH ROW EXECUTE FUNCTION alert_feedback_membership();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON alert_routing_decisions
 FOR EACH ROW EXECUTE FUNCTION immutable_record();
