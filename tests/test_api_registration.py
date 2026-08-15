from unittest import mock

from rcon.utils import ApiKey


def test_delete_key_only_removes_owned_registration():
    api_key = ApiKey.__new__(ApiKey)
    api_key.key = "frontend_4"
    api_key.red = mock.Mock()
    api_key.red.eval.return_value = 1

    assert api_key.delete_key(expected_key="owned-registration") is True
    api_key.red.eval.assert_called_once()
    args = api_key.red.eval.call_args.args
    assert args[1:] == (1, "frontend_4", "owned-registration")


def test_delete_key_reports_replaced_registration_as_not_deleted():
    api_key = ApiKey.__new__(ApiKey)
    api_key.key = "frontend_4"
    api_key.red = mock.Mock()
    api_key.red.eval.return_value = 0

    assert api_key.delete_key(expected_key="old-registration") is False
