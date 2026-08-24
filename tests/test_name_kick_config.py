import re

import pytest
from pydantic import ValidationError

from rcon.user_config.name_kicks import NameKickUserConfig


UNREADABLE_NAME_PATTERN = r"(^[^a-zA-Z0-9äöüÄÖÜß\[\]]+$)"


def test_unreadable_name_template_matches_symbols_but_keeps_readable_names():
    expression = re.compile(UNREADABLE_NAME_PATTERN)

    assert expression.match("★★★")
    assert not expression.match("[FLN]Biene")
    assert not expression.match("Äpfel123")


@pytest.mark.parametrize("expression", ["", " ", "\t"])
def test_name_kick_config_rejects_empty_regular_expressions(expression):
    with pytest.raises(ValidationError, match="must not be empty"):
        NameKickUserConfig(regular_expressions=[expression])
