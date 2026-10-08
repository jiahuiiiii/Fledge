-- Explicit, bounded original-parent inspection; never an extra sentiment vote.
CREATE TABLE social_conversation_results (
 id uuid PRIMARY KEY,post_id uuid NOT NULL REFERENCES social_posts,attempt_id uuid NOT NULL UNIQUE,
 outcome text NOT NULL CHECK(outcome IN ('available','unavailable','source_changed','source_removed','failed')),
 parent_key text,parent_type text CHECK(parent_type IN ('story','comment')),
 title text,body text,url text,published_at timestamptz,checked_at timestamptz NOT NULL,
 explanation text NOT NULL,UNIQUE(post_id,id),
 CHECK((outcome='available')=(parent_key IS NOT NULL AND parent_type IS NOT NULL AND title IS NOT NULL AND body IS NOT NULL AND url IS NOT NULL AND published_at IS NOT NULL)),
 CHECK(published_at IS NULL OR published_at<=checked_at));
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON social_conversation_results FOR EACH ROW EXECUTE FUNCTION immutable_record();
CREATE TABLE social_conversation_state (
 post_id uuid PRIMARY KEY REFERENCES social_posts,attempt_id uuid,lease_until timestamptz,last_attempt_at timestamptz,
 latest_result_id uuid,FOREIGN KEY(post_id,latest_result_id) REFERENCES social_conversation_results(post_id,id));
GRANT SELECT ON social_conversation_results,social_conversation_state TO thesis_app;
GRANT SELECT,INSERT ON social_conversation_results TO thesis_source;
GRANT SELECT,INSERT,UPDATE ON social_conversation_state TO thesis_source;
