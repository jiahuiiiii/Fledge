"""Saved filing figures (migration 072).

financial_depth.present() rebuilds a company's figures from saved SEC data:
it hashes every original filing, reloads every amendment's HTML, parses the
filings and applies this account's reviewed recoveries; income flow and
revenue by segment do the same. Each finished result is saved per account,
per kind and per exact set of inputs (`basis`) and reused until an input
changes. The basis is built from small indexed columns only; saved
documents are immutable, so an id and content hash identify their bytes.
"""
import hashlib
import json
import logging
from datetime import date, datetime
from decimal import Decimal

from psycopg.types.json import Jsonb

from thesis.db import one, rows, transaction

# Bump when anything that shapes the saved result changes without changing
# one of the calculation METHOD constants below.
VERSION = "filing-figures-2"  # 2: recovery_basis no longer depends on fact order
# JSON has no dates or decimals; tag them so a saved result reads back equal.
TAGS = {datetime: "$datetime", date: "$date", Decimal: "$decimal"}


def encode(value):
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    for kind, tag in TAGS.items():
        if type(value) is kind:
            return {tag: str(value) if kind is Decimal else value.isoformat()}
    return value


def decode(value):
    if isinstance(value, list):
        return [decode(v) for v in value]
    if isinstance(value, dict):
        if len(value) == 1:
            (tag, text), = value.items()
            if tag == "$datetime":
                return datetime.fromisoformat(text)
            if tag == "$date":
                return date.fromisoformat(text)
            if tag == "$decimal":
                return Decimal(text)
        return {k: decode(v) for k, v in value.items()}
    return value


def owner_of(conn):
    return one(conn, "SELECT nullif(current_setting('app.user_id',true),'') owner")["owner"]


def basis(conn, iid):
    """Every input financial_depth.present() reads, as one hash."""
    from . import amendments, filing_facts, financial_depth, financial_recovery, income_flow, segment_revenue

    parts = dict(
        versions=[VERSION, financial_depth.METHOD, filing_facts.METHOD, amendments.METHOD, financial_recovery.METHOD,
                  income_flow.METHOD, segment_revenue.METHOD],
        sources=rows(conn, "SELECT id,entitlement FROM sources WHERE id IN ('sec-companyfacts','sec-disclosures') ORDER BY id"),
        payload=one(conn, """SELECT k.payload_id,k.checked_at,p.retrieved_at,c.cik FROM sec_payload_current k
            JOIN source_payloads p ON p.id=k.payload_id AND p.instrument_id=k.instrument_id
            JOIN sec_companies c ON c.instrument_id=k.instrument_id WHERE k.instrument_id=%s""", (iid,)),
        # Originals and amendments of every form: any new saved copy rebuilds.
        documents=one(conn, """SELECT count(*) n,md5(string_agg(concat_ws('|',id,url,form,source_id,accession,content_hash,
            available_at,published_at),',' ORDER BY id)) h FROM disclosure_documents WHERE instrument_id=%s""", (iid,)),
        # Which saved filings are the current annual and quarterly reports.
        current=rows(conn, "SELECT slot,document_id FROM disclosure_current WHERE instrument_id=%s ORDER BY slot,document_id", (iid,)),
        # This account's readings and their newest reviews (row-level security).
        recoveries=rows(conn, """SELECT r.id,r.document_id,r.created_at,
            (SELECT v.id FROM financial_recovery_reviews v WHERE v.reading_id=r.id ORDER BY v.created_at DESC,v.id DESC LIMIT 1) review
            FROM financial_recovery_readings r WHERE r.instrument_id=%s ORDER BY r.id""", (iid,)),
    )
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def cached(conn, iid, kind, build, keep=("available",)):
    """This account's saved `kind` result for the current inputs, or a fresh
    build that is saved when its status is in `keep`. Reads without an
    account always build and never save."""
    owner = owner_of(conn)
    key = hashlib.sha256(f"{kind}|{basis(conn, iid)}".encode()).hexdigest() if owner else None
    if key:
        saved = load(conn, iid, key)
        if saved is not None:
            return saved
    result = build(conn, iid)
    if key and result.get("status") in keep:
        save(owner, iid, key, result)
    return result


def load(conn, iid, key):
    row = one(conn, "SELECT depth FROM filing_figures WHERE instrument_id=%s AND basis=%s", (iid, key))
    if not row:
        return None
    return decode(row["depth"])


def save(owner, iid, key, depth):
    """Saved in its own short transaction: readers are often read-only."""
    try:
        value = encode(depth)
        with transaction(owner) as conn:
            conn.execute(
                "INSERT INTO filing_figures(owner_id,instrument_id,basis,depth) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (owner, iid, key, Jsonb(value)),
            )
    except Exception:
        # Saving is an optimisation; the computed figures are still returned.
        logging.getLogger("thesis").exception("Saving filing figures failed")
