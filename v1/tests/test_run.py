from run import batched


def test_batched_preserves_all_items():
    items = [{"pair_id": str(i)} for i in range(5)]
    assert list(batched(items, 2)) == [items[:2], items[2:4], items[4:]]
