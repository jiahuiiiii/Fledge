"""Hold background work for a short while after the computer wakes from sleep.

On macOS the uptime clock (CLOCK_UPTIME_RAW, also time.monotonic) pauses during
sleep while wall time keeps running, so a jump in their difference means the
computer slept. Power Nap wakes a sleeping Mac for a few seconds at a time; an
AI request sent then is cut off when it sleeps again, and the app never resends
a request that may already have been charged. So new work waits until the
computer has stayed awake for SETTLE_SECONDS (19 Oct 2026, 47 sleeps in one
night left 15 requests unfinished).
"""

import logging
import threading
import time

SETTLE_SECONDS = 90
SLEEP_JUMP_SECONDS = 30
_UPTIME = getattr(time, "CLOCK_UPTIME_RAW", None)

logger = logging.getLogger("thesis")


def _awake_clock():
    return time.clock_gettime(_UPTIME) if _UPTIME is not None else time.monotonic()


class Guard:
    def __init__(self, *, wall=time.time, awake=_awake_clock,
                 settle=SETTLE_SECONDS, jump=SLEEP_JUMP_SECONDS):
        self._wall, self._awake = wall, awake
        self._settle, self._jump = settle, jump
        self._offset = None
        self._hold_until = None
        self._lock = threading.Lock()

    def settled(self):
        """False while the computer has been awake for less than the settle time."""
        wall, awake = self._wall(), self._awake()
        with self._lock:
            offset = wall - awake
            if self._offset is not None and offset - self._offset > self._jump:
                self._hold_until = awake + self._settle
                logger.warning("The computer woke from sleep. Background checks and AI requests "
                               "wait %d seconds for the connection to return.", self._settle)
            # A backwards wall-clock correction lowers the baseline; it is not a sleep.
            self._offset = offset
            return self._hold_until is None or awake >= self._hold_until


GUARD = Guard()


def settled():
    return GUARD.settled()


class Backoff:
    """A polling pause that doubles after each failure and logs once per outage."""

    def __init__(self, base, *, name, ceiling=60.0):
        self.base, self.name, self.ceiling = base, name, ceiling
        self.failures = 0

    def delay(self):
        return min(self.ceiling, self.base * 2 ** min(self.failures, 16))

    def failed(self, exc):
        self.failures += 1
        if self.failures == 1:
            # Only the error type: transport text can contain URLs or tokens.
            logger.warning("%s failed (%s). Trying again with longer pauses, up to %d seconds.",
                           self.name, type(exc).__name__, self.ceiling)

    def succeeded(self):
        if self.failures:
            logger.warning("%s works again after %d failed attempt%s.", self.name,
                           self.failures, "" if self.failures == 1 else "s")
        self.failures = 0
