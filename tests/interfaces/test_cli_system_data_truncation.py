import json

from src.interfaces.cli.routing import truncate_data


def test_truncate_data_default_limits():
    value = json.dumps({"a": "b" * 100}, ensure_ascii=False)
    truncated = truncate_data(value, 50)

    assert truncated.endswith("...")
    assert len(truncated) == 53


def test_truncate_data_zero_disables_truncation():
    value = "x" * 80
    assert truncate_data(value, 0) == value
