import pytest

from myxa.errors import UserError
from myxa.version import Version


class TestVersion:
    def test_version_invalid_from_str_raises_user_error(self) -> None:
        with pytest.raises(UserError, match="Invalid version string: 100"):
            Version.new("100")
