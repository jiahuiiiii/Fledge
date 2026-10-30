-- A watch may check a saved idea for both its reasoning and its question.
-- Only widens the allowed values of the existing alert-focus columns; saved rows
-- and every existing meaning are unchanged. Approved by the owner on
-- 29 October 2026.
ALTER TABLE news_watches DROP CONSTRAINT news_watches_idea_purpose_check;
ALTER TABLE news_watches ADD CONSTRAINT news_watches_idea_purpose_check
 CHECK (idea_purpose IN ('reasoning','question','both'));
ALTER TABLE watch_checks DROP CONSTRAINT watch_checks_idea_purpose_check;
ALTER TABLE watch_checks ADD CONSTRAINT watch_checks_idea_purpose_check
 CHECK (idea_purpose IN ('reasoning','question','both'));
