import pytest

from src.interfaces.cli.main import _match_expect


def test_match_expect_ok_status_only():
    response = {"ok": True, "data": {"foo": "bar"}}
    assert _match_expect("ok", response) is True


@pytest.mark.parametrize(
    "response,expected",
    [
        ({"ok": True, "data": {"total_qty": 8, "item_id": "abc"}}, {"total_qty": 8}),
        ({"ok": True, "data": {"a": {"nested": 1}, "b": 2}}, {"a": {"nested": 1}}),
    ],
)
def test_match_expect_partial_data_accepts_extras(response, expected):
    assert _match_expect(expected, response) is True


@pytest.mark.parametrize(
    "response,expected",
    [
        ({"status": "error", "data": {"total_qty": 8}}, {"total_qty": 8}),
        ({"ok": True, "data": {"other": 1}}, {"total_qty": 8}),
        ({"ok": True, "data": []}, {"total_qty": 8}),
        ({"ok": True}, {"total_qty": 8}),
    ],
)
def test_match_expect_partial_data_rejects_missing_or_bad_status(response, expected):
    assert _match_expect(expected, response) is False
