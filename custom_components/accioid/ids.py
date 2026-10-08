"""Minimal ULID generation for stable, sortable identifier strings.

The target model uses ULIDs for action and event ids, so they are stored as
opaque 26-character Crockford base32 strings. Accioid only ever *generates*
them -- it never needs to decode or validate foreign ids -- which keeps the
implementation tiny: 48 bits of millisecond timestamp followed by 80 bits of
randomness, both base32-encoded.
"""

from __future__ import annotations

import os
import time

#: Crockford base32 alphabet: no I, L, O or U, to avoid transcription errors.
_CROCKFORD: str = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

#: A ULID's timestamp occupies 48 bits; ten base32 characters hold 50.
_TIMESTAMP_CHARS: int = 10
#: A ULID's randomness occupies 80 bits; sixteen base32 characters hold 80.
_RANDOMNESS_CHARS: int = 16


def _encode(value: int, length: int) -> str:
    """Encode ``value`` as ``length`` big-endian base32 characters."""
    chars: list[str] = []
    for _ in range(length):
        value, remainder = divmod(value, 32)
        chars.append(_CROCKFORD[remainder])
    return "".join(reversed(chars))


def new_ulid(*, timestamp_ms: int | None = None) -> str:
    """Return a fresh 26-character ULID, lexicographically sortable by time.

    ``timestamp_ms`` exists only so tests can pin the clock; normal callers
    leave it unset and get the current time.
    """
    timestamp = int(time.time() * 1000) if timestamp_ms is None else timestamp_ms
    randomness = int.from_bytes(os.urandom(10), "big")
    return _encode(timestamp, _TIMESTAMP_CHARS) + _encode(randomness, _RANDOMNESS_CHARS)
