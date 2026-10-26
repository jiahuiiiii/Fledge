-- The latest saved sentiment reading per company was found by sorting on the
-- cutoff inside each reading's packet, which unpacks every saved packet
-- (several MB each; about 0.8 s per company on 25 Oct 2026). Keep the same
-- value in its own column, set from the packet on every insert, and index it.
-- Additive: packets and results are unchanged. Approved by the owner on
-- 25 October 2026 (requested as 069; 069 and 070 were already taken).
ALTER TABLE sentiment_analyses ADD COLUMN cutoff timestamptz;

CREATE FUNCTION sentiment_analysis_cutoff() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 NEW.cutoff := (NEW.packet->>'cutoff')::timestamptz;
 RETURN NEW;
END $$;

CREATE TRIGGER sentiment_analysis_cutoff BEFORE INSERT ON sentiment_analyses
 FOR EACH ROW EXECUTE FUNCTION sentiment_analysis_cutoff();

-- Saved readings are immutable; only this one-time copy of an existing value
-- is allowed, inside this migration's transaction.
ALTER TABLE sentiment_analyses DISABLE TRIGGER immutable;
UPDATE sentiment_analyses SET cutoff=(packet->>'cutoff')::timestamptz;
ALTER TABLE sentiment_analyses ENABLE TRIGGER immutable;

CREATE INDEX sentiment_by_cutoff
 ON sentiment_analyses(instrument_id, cutoff DESC, created_at DESC, id DESC);
