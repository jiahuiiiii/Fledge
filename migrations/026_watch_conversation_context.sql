-- Optional original-parent acquisition before watched sentiment analysis.
-- Existing settings and immutable attempts remain opted out.
ALTER TABLE news_watches ADD COLUMN include_context boolean NOT NULL DEFAULT false;
ALTER TABLE watch_checks ADD COLUMN include_context boolean NOT NULL DEFAULT false;
