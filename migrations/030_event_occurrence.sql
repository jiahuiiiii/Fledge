ALTER TABLE version_events ADD COLUMN date_basis text NOT NULL DEFAULT 'report_publication' CHECK(date_basis IN ('report_publication','event_occurrence'));
