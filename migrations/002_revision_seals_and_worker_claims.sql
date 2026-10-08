-- A version's condition membership is part of its immutable meaning. Only its
-- creating transaction may insert conditions; old versions are sealed on upgrade.
ALTER TABLE thesis_versions ADD COLUMN creation_xid xid8 NOT NULL DEFAULT pg_current_xact_id();
CREATE FUNCTION condition_belongs_to_open_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM thesis_versions WHERE id=NEW.version_id
   AND owner_id=NEW.owner_id AND creation_xid=pg_current_xact_id()) THEN
   RAISE EXCEPTION 'The condition set of a committed revision is sealed';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sealed_membership BEFORE INSERT ON version_conditions
 FOR EACH ROW EXECUTE FUNCTION condition_belongs_to_open_revision();
ALTER TABLE jobs ADD COLUMN claim_token uuid;
