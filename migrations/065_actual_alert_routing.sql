-- Enable new actual publications, never promote existing preview records.
DO $$ DECLARE c text; BEGIN
 FOR c IN SELECT conname FROM pg_constraint WHERE conrelid='research_alerts'::regclass
  AND contype='c' AND pg_get_constraintdef(oid) LIKE '%important_reporting%'
  AND pg_get_constraintdef(oid) LIKE '%preview%'
 LOOP EXECUTE format('ALTER TABLE research_alerts DROP CONSTRAINT %I',c); END LOOP;
END $$;

-- A preview failure/backoff must not delay a separately approved activation.
ALTER TABLE daily_updates_state ADD COLUMN policy text NOT NULL DEFAULT 'daily-updates-1';
