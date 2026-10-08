ALTER TABLE version_events ADD COLUMN repeat_months integer NOT NULL DEFAULT 0 CHECK(repeat_months IN (0,1,3,12));
ALTER TABLE version_events ADD COLUMN repeat_count integer NOT NULL DEFAULT 1 CHECK(repeat_count BETWEEN 1 AND 12);
ALTER TABLE version_events ADD CHECK((repeat_months=0 AND repeat_count=1) OR (repeat_months<>0 AND repeat_count>=2));
