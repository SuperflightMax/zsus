from src.interfaces.cli.routing import classify_input


def test_classify_input_admin_prefix():
    assert classify_input("+status") == "admin"


def test_classify_input_json_prefix():
    assert classify_input("{\"command\":\"list\"}") == "json"


def test_classify_input_user_text():
    assert classify_input("привіт") == "user"
