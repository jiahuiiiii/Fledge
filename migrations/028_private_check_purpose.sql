-- Explicit user-selected private check purpose; preserve existing broad checks.
ALTER TABLE news_watches ADD COLUMN idea_purpose text NOT NULL DEFAULT 'reasoning'
 CHECK (idea_purpose IN ('reasoning','question'));
ALTER TABLE watch_checks ADD COLUMN idea_purpose text NOT NULL DEFAULT 'reasoning'
 CHECK (idea_purpose IN ('reasoning','question'));
