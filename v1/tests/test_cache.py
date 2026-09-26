from cache import DiskCache


def test_cache_key_is_stable_across_dict_order():
    assert DiskCache.key({"a": 1, "b": 2}) == DiskCache.key({"b": 2, "a": 1})


def test_cache_round_trip(tmp_path):
    cache = DiskCache(tmp_path)
    payload = {"model": "test", "input": "hello"}
    cache.put(payload, {"text": "world"})
    assert cache.get(payload) == {"text": "world"}

