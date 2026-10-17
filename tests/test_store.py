"""Testes da camada de persistência (Store). Rodam headless, sem GTK."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clipdev import store as st  # noqa: E402


def make_store(tmp_path, max_unpinned=50):
    return st.Store(path=str(tmp_path / "test.db"), max_unpinned=max_unpinned)


def add_text(s, text, t=None):
    h = st.Store.hash_content(text.encode())
    return s.add(st.TEXT, text, text, h)


def test_add_and_list(tmp_path):
    s = make_store(tmp_path)
    add_text(s, "primeiro")
    add_text(s, "segundo")
    items = s.list_items()
    assert [i["content"] for i in items] == ["segundo", "primeiro"]
    assert s.count() == 2


def test_dedup_bumps_to_top(tmp_path):
    s = make_store(tmp_path)
    add_text(s, "a")
    add_text(s, "b")
    _, created = add_text(s, "a")
    assert created is False
    assert s.count() == 2
    assert s.list_items()[0]["content"] == "a"


def test_retention_keeps_max_unpinned(tmp_path):
    s = make_store(tmp_path, max_unpinned=50)
    for i in range(60):
        add_text(s, f"item-{i}")
    assert s.count_unpinned() == 50
    contents = [i["content"] for i in s.list_items()]
    # os 10 mais antigos foram removidos
    assert "item-0" not in contents
    assert "item-9" not in contents
    assert "item-10" in contents
    assert "item-59" in contents


def test_pinned_survive_retention(tmp_path):
    s = make_store(tmp_path, max_unpinned=5)
    _, created = add_text(s, "pin-me")
    assert created
    pin_id = s.list_items()[0]["id"]
    s.set_pinned(pin_id, True)
    for i in range(20):
        add_text(s, f"x{i}")
    ids = [i["id"] for i in s.list_items()]
    assert pin_id in ids
    assert s.get(pin_id)["pinned"] == 1
    assert s.count_unpinned() == 5


def test_pinned_sorted_first(tmp_path):
    s = make_store(tmp_path)
    add_text(s, "novo")
    add_text(s, "velho")
    old_id = [i for i in s.list_items() if i["content"] == "velho"][0]["id"]
    s.set_pinned(old_id, True)
    assert s.list_items()[0]["content"] == "velho"


def test_toggle_pinned(tmp_path):
    s = make_store(tmp_path)
    add_text(s, "x")
    item_id = s.list_items()[0]["id"]
    assert s.toggle_pinned(item_id) is True
    assert s.get(item_id)["pinned"] == 1
    assert s.toggle_pinned(item_id) is False
    assert s.get(item_id)["pinned"] == 0


def test_search_filter(tmp_path):
    s = make_store(tmp_path)
    add_text(s, "maçã verde")
    add_text(s, "banana")
    add_text(s, "maçã vermelha")
    res = s.list_items(query="maçã")
    assert len(res) == 2
    assert all("maçã" in i["content"] for i in res)


def test_clear_unpinned_keeps_pinned(tmp_path):
    s = make_store(tmp_path)
    add_text(s, "a")
    add_text(s, "b")
    pin_id = s.list_items()[0]["id"]
    s.set_pinned(pin_id, True)
    removed = s.clear_unpinned()
    assert removed == 1
    assert s.count() == 1
    assert s.get(pin_id)["pinned"] == 1


def test_delete(tmp_path):
    s = make_store(tmp_path)
    add_text(s, "some")
    item_id = s.list_items()[0]["id"]
    s.delete(item_id)
    assert s.count() == 0