import argparse

import pytest

from maestro_worker_python.server import _parse_bool


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_parse_bool_accepts_true_values(value):
    assert _parse_bool(value) is True


@pytest.mark.parametrize("value", ["0", "false", "FALSE", "no", "off"])
def test_parse_bool_accepts_false_values(value):
    assert _parse_bool(value) is False


def test_parse_bool_rejects_unknown_value():
    with pytest.raises(argparse.ArgumentTypeError, match="expected a boolean value"):
        _parse_bool("sometimes")
