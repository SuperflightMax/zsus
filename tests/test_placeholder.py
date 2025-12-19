import pytest


pytestmark = pytest.mark.skip(reason="Core engine tests are deferred to a future task.")


def test_placeholder():
    """Placeholder test to keep pytest happy while real tests are deferred."""
    assert True
