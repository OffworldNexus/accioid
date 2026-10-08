"""Tests for the ULID generator."""

from __future__ import annotations

from custom_components.accioid.ids import new_ulid

_ALPHABET = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")


def test_ulid_shape() -> None:
    """A ULID is 26 Crockford base32 characters."""
    value = new_ulid()
    assert len(value) == 26
    assert set(value) <= _ALPHABET


def test_ulid_is_time_sortable() -> None:
    """Earlier timestamps produce lexicographically smaller ULIDs."""
    assert new_ulid(timestamp_ms=1_000) < new_ulid(timestamp_ms=2_000)


def test_ulid_is_unique() -> None:
    """A thousand ULIDs generated in a tight loop never collide."""
    assert len({new_ulid() for _ in range(1000)}) == 1000
