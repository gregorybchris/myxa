import re

import pytest

from myxa.errors import UserError
from myxa.models import Index, Version


class TestModels:
    def test_version_invalid_from_str_raises_user_error(self) -> None:
        with pytest.raises(UserError, match="Invalid version string: 100"):
            Version.from_str("100")

    def test_package_not_found_in_index_raises_user_error(
        self,
        primary_index: Index,
    ) -> None:
        with pytest.raises(UserError, match=re.escape("Package euler not found in the provided index: primary")):
            primary_index.get_namespace("euler")
