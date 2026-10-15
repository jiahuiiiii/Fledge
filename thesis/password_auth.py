"""Username and password sign-in for the test product.

Passwords are stored only as salted scrypt hashes. Sessions are opaque random
cookies whose SHA-256 digest is kept server-side, like the email sign-in.
Repeated wrong passwords are slowed down per username and per installation.
"""
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import math
import re
import secrets
from uuid import uuid4
from .config import OWNER
from .db import transaction, one

SESSION_DAYS = 7
USERNAME = re.compile(r'[a-z0-9_.-]{3,30}')
SCRYPT = dict(n=2**14, r=8, p=1, dklen=32)
# Per-username and installation-wide limits on failed sign-ins.
LIMITS = (('user', 5, 15 * 60), ('global', 50, 15 * 60))


class PasswordFailure(Exception):
    def __init__(self, message, status=401, retry_after=None):
        self.status = status
        self.retry_after = retry_after
        super().__init__(message)


def normalize(username):
    value = (username or '').strip().casefold()
    if not USERNAME.fullmatch(value):
        raise PasswordFailure('Use 3–30 letters, numbers, dots, dashes or underscores for your username.', 422)
    return value


def check_password(password):
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise PasswordFailure('Use a password of 8 to 128 characters.', 422)


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return 'scrypt$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(key).decode()


def verify(password, stored):
    try:
        kind, salt, key = stored.split('$')
        if kind != 'scrypt':
            return False
        expected = hash_password(password, base64.b64decode(salt)).split('$')[2]
        return hmac.compare_digest(expected, key)
    except (ValueError, TypeError):
        return False


DUMMY = hash_password(secrets.token_urlsafe(16))


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_session(conn, account, now):
    cookie = secrets.token_urlsafe(32)
    conn.execute('DELETE FROM password_sessions WHERE expires_at<%s', (now,))
    conn.execute('INSERT INTO password_sessions(token_hash,account_id,expires_at) VALUES(%s,%s,%s)',
                 (digest(cookie), account, now + timedelta(days=SESSION_DAYS)))
    return cookie, SESSION_DAYS * 86400


def register(username, password, *, now=None, terms_version=None):
    """Public sign-up. Always creates a new, separate account.

    ``terms_version`` records the Terms of Use and Privacy Notice the person
    accepted, in the same transaction as the account (PDPA consent record).
    """
    name = normalize(username)
    check_password(password)
    now = now or datetime.now(timezone.utc)
    hashed = hash_password(password)
    with transaction(admin=True) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('fledge-password-register'))")
        if one(conn, 'SELECT 1 FROM password_credentials WHERE username=%s', (name,)):
            raise PasswordFailure('That username is taken. Choose another.', 409)
        account = str(uuid4())
        conn.execute('INSERT INTO accounts VALUES(%s,%s)', (account, 'Research account'))
        conn.execute('INSERT INTO password_credentials(account_id,username,password_hash) VALUES(%s,%s,%s)',
                     (account, name, hashed))
        if terms_version:
            conn.execute('INSERT INTO terms_acceptances(account_id,terms_version,accepted_at) VALUES(%s,%s,%s)',
                         (account, terms_version, now))
        return new_session(conn, account, now)


def provision_owner(username, password):
    """Give the installation owner a username and password.

    Run only from the server's own shell (``python -m thesis.password_auth
    owner <username>``), never through the web sign-up, so having shell access
    to the machine is what proves ownership. Refuses if the owner already has a
    login or the username belongs to someone else.
    """
    name = normalize(username)
    check_password(password)
    hashed = hash_password(password)
    with transaction(admin=True) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('fledge-password-register'))")
        if one(conn, 'SELECT 1 FROM password_credentials WHERE account_id=%s', (OWNER,)):
            raise PasswordFailure('The installation owner already has a login.', 409)
        if one(conn, 'SELECT 1 FROM password_credentials WHERE username=%s', (name,)):
            raise PasswordFailure('That username is taken. Choose another.', 409)
        conn.execute("INSERT INTO accounts VALUES(%s,'Installation owner') ON CONFLICT DO NOTHING", (OWNER,))
        conn.execute('INSERT INTO password_credentials(account_id,username,password_hash) VALUES(%s,%s,%s)',
                     (OWNER, name, hashed))
    return name


def _admit(conn, name, now):
    """Reserve one attempt against every limit, or return the wait in seconds.

    The counter rows are locked and the attempt is counted *before* the
    password is checked, all in one committed transaction. Concurrent requests
    therefore queue on the row locks and each sees the attempts admitted
    before it, so a burst cannot slip past the limit. A correct password gives
    its reserved attempt back.
    """
    rows = []
    for scope, limit, seconds in sorted(LIMITS, key=lambda item: item[0]):  # fixed lock order
        key = scope if scope == 'global' else 'user:' + name
        conn.execute('INSERT INTO password_attempts VALUES(%s,%s,0) ON CONFLICT DO NOTHING', (key, now))
        state = one(conn, 'SELECT * FROM password_attempts WHERE key=%s FOR UPDATE', (key,))
        if now - state['window_start'] >= timedelta(seconds=seconds):
            conn.execute('UPDATE password_attempts SET window_start=%s,failures=0 WHERE key=%s', (now, key))
        elif state['failures'] >= limit:
            return max(1, math.ceil((state['window_start'] + timedelta(seconds=seconds) - now).total_seconds()))
        rows.append(key)
    for key in rows:
        conn.execute('UPDATE password_attempts SET failures=failures+1 WHERE key=%s', (key,))
    return None


def login(username, password, *, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        name = normalize(username)
    except PasswordFailure:
        raise PasswordFailure('Username or password is incorrect.') from None
    with transaction(admin=True) as conn:
        wait = _admit(conn, name, now)
    if wait:
        raise PasswordFailure('Too many attempts. Try again after the countdown.', 429, wait)
    with transaction(admin=True) as conn:
        row = one(conn, 'SELECT account_id,password_hash FROM password_credentials WHERE username=%s', (name,))
    # Hash even for unknown usernames so timing does not reveal which exist.
    ok = verify(password or '', row['password_hash'] if row else DUMMY) and row is not None
    if not ok:
        # The attempt was already counted when it was admitted.
        raise PasswordFailure('Username or password is incorrect.')
    with transaction(admin=True) as conn:
        conn.execute('UPDATE password_attempts SET failures=0 WHERE key=%s', ('user:' + name,))
        conn.execute('UPDATE password_attempts SET failures=GREATEST(failures-1,0) WHERE key=%s', ('global',))
        return new_session(conn, str(row['account_id']), now)


def authenticate(cookie, *, now=None):
    if not cookie or len(cookie) > 256:
        return None
    now = now or datetime.now(timezone.utc)
    with transaction(admin=True) as conn:
        row = one(conn, 'SELECT account_id,expires_at FROM password_sessions WHERE token_hash=%s', (digest(cookie),))
    if not row or row['expires_at'] <= now:
        return None
    return str(row['account_id'])


def logout(cookie):
    if cookie:
        with transaction(admin=True) as conn:
            conn.execute('DELETE FROM password_sessions WHERE token_hash=%s', (digest(cookie),))


def username(account):
    with transaction(admin=True) as conn:
        row = one(conn, 'SELECT username FROM password_credentials WHERE account_id=%s', (account,))
    return row['username'] if row else None


def owners():
    with transaction(admin=True) as conn:
        return [str(r['account_id']) for r in conn.execute('SELECT account_id FROM password_credentials ORDER BY account_id').fetchall()]


if __name__ == '__main__':
    import argparse
    import getpass
    import sys
    parser = argparse.ArgumentParser(description='Manage username sign-in from the server shell.')
    sub = parser.add_subparsers(dest='command', required=True)
    owner_cmd = sub.add_parser('owner', help='Give the installation owner (existing research) a username and password.')
    owner_cmd.add_argument('username')
    args = parser.parse_args()
    first = getpass.getpass('New password: ')
    if first != getpass.getpass('Repeat password: '):
        sys.exit('Passwords did not match.')
    try:
        print('Owner can now sign in as', provision_owner(args.username, first))
    except PasswordFailure as failure:
        sys.exit(str(failure))
