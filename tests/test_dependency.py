from myxa.dependency import Dependency
from myxa.version import Version


class TestDependency:
    def test_to_str(self) -> None:
        dependency = Dependency.new("euler", "1.2")
        assert str(dependency) == "euler~=1.2"

    def test_higher_minor_satisfies_lower_minor(self) -> None:
        version = Version.new("1.2")
        dependency = Dependency.new("euler", "1.1")
        assert dependency.is_satisfied_by(version)

    def test_lower_minor_does_not_satisfy_higher_minor(self) -> None:
        version = Version.new("1.1")
        dependency = Dependency.new("euler", "1.2")
        assert not dependency.is_satisfied_by(version)

    def test_higher_major_does_not_satisfy_lower_major(self) -> None:
        version = Version.new("2.0")
        dependency = Dependency.new("euler", "1.2")
        assert not dependency.is_satisfied_by(version)

    def test_lower_major_does_not_satisfy_higher_major(self) -> None:
        version = Version.new("0.1")
        dependency = Dependency.new("euler", "1.0")
        assert not dependency.is_satisfied_by(version)

    def test_same_version_satisfies_dep(self) -> None:
        version = Version.new("1.2")
        dependency = Dependency.new("euler", "1.2")
        assert dependency.is_satisfied_by(version)
