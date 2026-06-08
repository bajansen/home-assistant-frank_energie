import pytest

from custom_components.frank_energie.sensor import _safe_attributes, _safe_value


@pytest.mark.parametrize(
    "exception",
    [
        TypeError,
        IndexError,
        ValueError,
        AttributeError,
        ZeroDivisionError,
    ],
)
def test_safe_value_returns_none_when_data_is_unavailable(exception):
    """Test missing API data makes a sensor unavailable instead of raising."""

    def value_fn(_):
        raise exception

    assert _safe_value(value_fn, {}) is None


@pytest.mark.parametrize(
    "exception",
    [
        TypeError,
        IndexError,
        ValueError,
        AttributeError,
        ZeroDivisionError,
    ],
)
def test_safe_attributes_returns_empty_dict_when_data_is_unavailable(exception):
    """Test missing API data omits attributes instead of raising."""

    def attr_fn(_):
        raise exception

    assert _safe_attributes(attr_fn, {}) == {}


def test_safe_value_returns_value_when_data_is_available():
    """Test regular values are returned unchanged."""

    assert _safe_value(lambda data: data["value"], {"value": 1.23}) == 1.23


def test_safe_attributes_returns_attributes_when_data_is_available():
    """Test regular attributes are returned unchanged."""

    attributes = {"prices": [{"price": 1.23}]}

    assert _safe_attributes(lambda _: attributes, {}) == attributes
