ALTER TABLE version_conditions ADD COLUMN expected_period_end date;
ALTER TABLE version_conditions ADD COLUMN expected_report_by date;
ALTER TABLE version_conditions ADD CHECK (
 (expected_period_end IS NULL AND expected_report_by IS NULL) OR
 (expected_period_end IS NOT NULL AND expected_report_by IS NOT NULL
  AND expected_report_by >= expected_period_end
  AND expected_report_by - expected_period_end <= 3650
  AND expected_report_by < DATE '9999-12-31')
);
ALTER TABLE change_events DROP CONSTRAINT change_events_kind_check;
ALTER TABLE change_events ADD CHECK(kind IN ('figures','coverage','evidence','expiry','event','reporting'));
