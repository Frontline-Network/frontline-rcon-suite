import pytest

from rcon.barricade_blacklist_reconcile import compare_snapshots


def test_existing_records_are_classified_without_ownership_assumptions():
    result = compare_snapshots([1, 2], ['2', '3'])
    assert result.referenced_and_present == {2}
    assert result.referenced_but_missing == {3}
    assert result.present_but_unreferenced == {1}


@pytest.mark.parametrize('frontline,peer', [
    ([1, 1], []), ([1, '1'], []), ([], ['2', 2]),
    ([True], []), ([0], []), ([-1], []), ([], ['01']),
    ([], ['-1']), ([], ['1.0']), ([], ['']), ([], [None]),
])
def test_ambiguous_or_invalid_ids_are_rejected(frontline, peer):
    with pytest.raises(ValueError):
        compare_snapshots(frontline, peer)


def test_empty_snapshots_are_valid_but_not_proof_of_completeness():
    result = compare_snapshots([], [])
    assert not result.referenced_and_present
    assert not result.referenced_but_missing
    assert not result.present_but_unreferenced
