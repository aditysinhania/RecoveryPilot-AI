"""Scheduler backoff: 1m, 5m, 30m, then 2h, each with symmetric jitter. Dead-letter after the last slot."""

from __future__ import annotations

import random
from datetime import timedelta

BACKOFF_STEPS: tuple[timedelta, ...] = (
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=30),
    timedelta(hours=2),
)

JITTER_WINDOWS: tuple[timedelta, ...] = (
    timedelta(seconds=15),
    timedelta(seconds=45),
    timedelta(minutes=2),
    timedelta(minutes=5),
)

MAX_RETRY_ATTEMPTS: int = len(BACKOFF_STEPS)


def next_backoff(attempt: int, *, rng: random.Random | None = None) -> timedelta | None:
    """Return the jittered delay before the next retry, or ``None`` to dead-letter.

    Windows: 1m±15s, 5m±45s, 30m±2m, 2h±5m. Attempt count and dead-letter after
    four retries are unchanged.

    Args:
        attempt: Zero-based count of transient failures already recorded.
        rng: Optional RNG so tests can pin jitter. Production uses a fresh Random.

    Returns:
        Delay until the next run, or ``None`` when the retry budget is exhausted.
    """
    if attempt < 0:
        attempt = 0
    if attempt >= MAX_RETRY_ATTEMPTS:
        return None
    base = BACKOFF_STEPS[attempt]
    jitter = JITTER_WINDOWS[attempt]
    generator = rng if rng is not None else random.Random()
    offset = generator.uniform(-jitter.total_seconds(), jitter.total_seconds())
    delay = base + timedelta(seconds=offset)
    if delay.total_seconds() < 1:
        return timedelta(seconds=1)
    return delay
