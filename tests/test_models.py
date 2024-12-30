import pytest

from myxa.errors import UserError
from myxa.models import Version


class TestModels:
    def test_version_invalid_from_str_raises_user_error(self) -> None:
        with pytest.raises(UserError, match="Invalid version string: 100"):
            Version.from_str("100")
