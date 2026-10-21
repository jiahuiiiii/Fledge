"""Username and password sign-in for the test product.

Passwords and recovery codes are stored only as salted scrypt hashes. A
recovery code (shown once, at sign-up or when replaced) lets someone set a new
password without email; using it signs out every other session and issues a
new code. Sessions are opaque random
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


# Recovery codes: 16 characters without look-alikes (no 0/O, 1/I/L), in four
# groups, e.g. K7QF-2MXP-9TRA-H4WN. About 78 bits; attempts are rate limited.
RECOVERY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def new_recovery_code():
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(16))
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))


def clean_code(code):
    """Accept the code typed with or without dashes, spaces or lower case."""
    raw = re.sub(r"[\s-]", "", (code or "").upper())
    return "-".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def set_recovery(conn, account, now):
    code = new_recovery_code()
    conn.execute('UPDATE password_credentials SET recovery_hash=%s,recovery_set_at=%s WHERE account_id=%s',
                 (hash_password(code), now, account))
    return code


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
        code = set_recovery(conn, account, now)
        return (*new_session(conn, account, now), code)


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


def reset_with_code(username, code, new_password, *, now=None):
    """Forgot password: the recovery code sets a new password.

    Counts against the same per-username and installation-wide attempt limits
    as sign-in. Success signs out every session, issues a new recovery code
    (the old one stops working) and signs this browser in.
    """
    now = now or datetime.now(timezone.utc)
    check_password(new_password)
    try:
        name = normalize(username)
    except PasswordFailure:
        raise PasswordFailure('Username or recovery code is incorrect.') from None
    with transaction(admin=True) as conn:
        wait = _admit(conn, name, now)
    if wait:
        raise PasswordFailure('Too many attempts. Try again after the countdown.', 429, wait)
    with transaction(admin=True) as conn:
        row = one(conn, 'SELECT account_id,recovery_hash FROM password_credentials WHERE username=%s', (name,))
    stored = row['recovery_hash'] if row and row['recovery_hash'] else DUMMY
    if not (verify(clean_code(code), stored) and row and row['recovery_hash']):
        raise PasswordFailure('Username or recovery code is incorrect.')
    account = str(row['account_id'])
    with transaction(admin=True) as conn:
        conn.execute('UPDATE password_credentials SET password_hash=%s WHERE account_id=%s',
                     (hash_password(new_password), account))
        conn.execute('DELETE FROM password_sessions WHERE account_id=%s', (account,))
        conn.execute('UPDATE password_attempts SET failures=0 WHERE key=%s', ('user:' + name,))
        fresh = set_recovery(conn, account, now)
        return (*new_session(conn, account, now), fresh)


def _check_current(account, password, now):
    with transaction(admin=True) as conn:
        row = one(conn, 'SELECT username,password_hash FROM password_credentials WHERE account_id=%s', (account,))
    if not row:
        raise PasswordFailure('This account has no username sign-in.', 409)
    with transaction(admin=True) as conn:
        wait = _admit(conn, row['username'], now)
    if wait:
        raise PasswordFailure('Too many attempts. Try again after the countdown.', 429, wait)
    if not verify(password or '', row['password_hash']):
        raise PasswordFailure('Your current password is incorrect.', 403)
    return row['username']


def change_password(account, current, new_password, *, now=None):
    """Signed in: change the password after re-entering the current one.
    Every other session is signed out; this browser gets a fresh session."""
    now = now or datetime.now(timezone.utc)
    check_password(new_password)
    name = _check_current(account, current, now)
    with transaction(admin=True) as conn:
        conn.execute('UPDATE password_credentials SET password_hash=%s WHERE account_id=%s',
                     (hash_password(new_password), account))
        conn.execute('DELETE FROM password_sessions WHERE account_id=%s', (account,))
        conn.execute('UPDATE password_attempts SET failures=0 WHERE key=%s', ('user:' + name,))
        return new_session(conn, account, now)


def replace_recovery_code(account, current, *, now=None):
    """Signed in: show a new recovery code after re-entering the password.
    Accounts made before recovery codes existed use this to get their first."""
    now = now or datetime.now(timezone.utc)
    name = _check_current(account, current, now)
    with transaction(admin=True) as conn:
        conn.execute('UPDATE password_attempts SET failures=0 WHERE key=%s', ('user:' + name,))
        return set_recovery(conn, account, now)


def has_recovery(account):
    with transaction(admin=True) as conn:
        row = one(conn, 'SELECT recovery_hash IS NOT NULL ok FROM password_credentials WHERE account_id=%s',
                  (account,))
    return bool(row and row['ok'])


def admin_reset(username, new_password):
    """Server shell only: someone lost both password and recovery code. The
    person running Fledge sets a temporary password and tells them privately."""
    name = normalize(username)
    check_password(new_password)
    with transaction(admin=True) as conn:
        row = one(conn, 'SELECT account_id FROM password_credentials WHERE username=%s', (name,))
        if not row:
            raise PasswordFailure('No account has that username.', 404)
        # The lost code may be in someone else's hands: it stops working too.
        conn.execute('UPDATE password_credentials SET password_hash=%s, recovery_hash=NULL, '
                     'recovery_set_at=NULL WHERE account_id=%s',
                     (hash_password(new_password), row['account_id']))
        conn.execute('DELETE FROM password_sessions WHERE account_id=%s', (row['account_id'],))
        conn.execute('DELETE FROM password_attempts WHERE key=%s', ('user:' + name,))
    return name


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
    reset_cmd = sub.add_parser('reset', help='Set a temporary password for someone who lost both password and recovery code.')
    reset_cmd.add_argument('username')
    args = parser.parse_args()
    first = getpass.getpass('New password: ')
    if first != getpass.getpass('Repeat password: '):
        sys.exit('Passwords did not match.')
    try:
        if args.command == 'owner':
            print('Owner can now sign in as', provision_owner(args.username, first))
        else:
            print('Temporary password set for', admin_reset(args.username, first),
                  '- they should change it in Account after signing in.')
    except PasswordFailure as failure:
        sys.exit(str(failure))
