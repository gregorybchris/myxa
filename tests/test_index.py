import re

import pytest

from myxa.errors import UserError
from myxa.index import Index


class TestIndex:
    def test_package_not_found_in_index_raises_user_error(self, primary_index: Index) -> None:
        with pytest.raises(UserError, match=re.escape("Package euler not found in the provided index: primary")):
            primary_index._get_namespace("euler")
