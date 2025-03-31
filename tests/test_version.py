import pytest
import semver

from myxa import __version__
from myxa.errors import UserError
from myxa.version import Version


class TestVersion:
    def test_version(self) -> None:
        version = semver.VersionInfo.parse(__version__)
        assert version.major == 0
        assert version.minor > 0

    def test_version_invalid_from_str_raises_user_error(self) -> None:
        with pytest.raises(UserError, match="Invalid version string: 100"):
            Version.new("100")
