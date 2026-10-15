"""Terms of Use and Privacy Notice consent (Singapore PDPA).

VERSION must match TERMS_VERSION in frontend/src/lib/terms.js. Changing the
text in a way that needs fresh consent means bumping both; every signed-in
account is then asked to accept the new version once.
"""
from .db import transaction, one

VERSION = '2026-10-15'


def status(owner):
    with transaction(owner) as conn:
        row = one(conn, 'SELECT accepted_at FROM terms_acceptances WHERE account_id=%s AND terms_version=%s',
                  (owner, VERSION))
    return {'version': VERSION, 'accepted': bool(row),
            'accepted_at': row['accepted_at'].isoformat() if row else None}


def accept(owner, version):
    if version != VERSION:
        raise ValueError('These terms have changed. Reload the page to read the current version.')
    with transaction(owner) as conn:
        conn.execute('''INSERT INTO terms_acceptances(account_id,terms_version) VALUES(%s,%s)
            ON CONFLICT DO NOTHING''', (owner, version))
    return status(owner)
