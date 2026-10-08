-- Optional user-defined evidence horizon. Existing definitions remain unlimited.
ALTER TABLE version_conditions ADD COLUMN max_report_age_days integer
 CHECK(max_report_age_days BETWEEN 1 AND 3650);
ALTER TABLE monitoring_cursors ADD COLUMN assessed_through timestamptz;
ALTER TABLE jobs ADD COLUMN queue_order bigint;
WITH ordered AS (SELECT id,row_number() OVER(ORDER BY coalesce((manifest->>'snapshot_id')::bigint,0),created_at,id) n FROM jobs)
 UPDATE jobs SET queue_order=ordered.n FROM ordered WHERE jobs.id=ordered.id;
CREATE SEQUENCE job_queue_order;
SELECT setval('job_queue_order',coalesce((SELECT max(queue_order) FROM jobs),0)+1,false);
ALTER TABLE jobs ALTER COLUMN queue_order SET DEFAULT nextval('job_queue_order');
ALTER TABLE jobs ALTER COLUMN queue_order SET NOT NULL;
CREATE UNIQUE INDEX job_queue_order_unique ON jobs(queue_order);
GRANT USAGE ON SEQUENCE job_queue_order TO thesis_app;
