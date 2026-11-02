"""The current saved SEC payload for a company, decoded once.

`source_payloads` rows never change (the `immutable` trigger refuses UPDATE
and DELETE), and each payload is the company's whole SEC companyfacts and
submissions JSON, often megabytes. Decoding it took 0.4–1.5 s on every
Financials read. The small pointer (which payload is current, when it was
checked, the CIK) is read every time, so a refresh is seen at once; only the
decoded payload is kept, by id. Callers get their own copy.
"""
from collections import OrderedDict
import pickle
import threading

from thesis.db import one

CACHE_BYTES = 96 * 1024 * 1024
_payloads = OrderedDict()
_bytes = 0
_lock = threading.Lock()

POINTER_SQL = (
    "SELECT k.payload_id id,p.retrieved_at,c.cik,k.checked_at FROM sec_payload_current k"
    " JOIN source_payloads p ON p.id=k.payload_id AND p.instrument_id=k.instrument_id"
    " JOIN sec_companies c ON c.instrument_id=k.instrument_id WHERE k.instrument_id=%s"
)


def clear():
    global _bytes
    with _lock:
        _payloads.clear()
        _bytes = 0


def payload(conn, payload_id):
    global _bytes
    key = str(payload_id)
    with _lock:
        blob = _payloads.get(key)
        if blob is not None:
            _payloads.move_to_end(key)
    if blob is None:
        row = one(conn, "SELECT payload FROM source_payloads WHERE id=%s", (payload_id,))
        if not row:
            return None
        blob = pickle.dumps(row["payload"], pickle.HIGHEST_PROTOCOL)
        if len(blob) <= CACHE_BYTES // 4:
            with _lock:
                if key not in _payloads:
                    _payloads[key] = blob
                    _bytes += len(blob)
                while _bytes > CACHE_BYTES and _payloads:
                    _, removed = _payloads.popitem(last=False)
                    _bytes -= len(removed)
    return pickle.loads(blob)


def current(conn, iid):
    """Same fields as the old joined query: id, payload, retrieved_at, cik,
    checked_at; None when the company has no saved payload."""
    pointer = one(conn, POINTER_SQL, (iid,))
    if not pointer:
        return None
    body = payload(conn, pointer["id"])
    return dict(pointer, payload=body) if body is not None else None
