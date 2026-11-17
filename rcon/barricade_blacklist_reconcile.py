"""Read-only comparison of complete snapshots for a single peer and list.

An overlap proves only that the peer references a record. It does not prove
that the peer created the ban, nor does it authorize adopting or removing it.
Snapshot acquisition, list/game scoping and quiescence must be verified by
the caller; a partial snapshot is never safe to use for a decision.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SnapshotComparison:
    referenced_and_present: frozenset[int]
    referenced_but_missing: frozenset[int]
    present_but_unreferenced: frozenset[int]


def _record_ids(values):
    result = set()
    for value in values:
        if isinstance(value, bool):
            raise ValueError('Invalid blacklist record ID')
        if isinstance(value, str):
            if not value.isascii() or not value.isdecimal() or str(int(value)) != value:
                raise ValueError('Invalid blacklist record ID')
            value = int(value)
        if type(value) is not int or value <= 0:
            raise ValueError('Invalid blacklist record ID')
        if value in result:
            raise ValueError('Duplicate blacklist record ID')
        result.add(value)
    return result


def compare_snapshots(frontline_record_ids, peer_remote_ids):
    """Compare two independently acquired, complete snapshots; never write."""
    frontline = _record_ids(frontline_record_ids)
    peer = _record_ids(peer_remote_ids)
    return SnapshotComparison(frozenset(frontline & peer), frozenset(peer - frontline),
                              frozenset(frontline - peer))
