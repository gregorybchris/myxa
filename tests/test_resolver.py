import pytest

from myxa.errors import UserError
from myxa.manager import Manager
from myxa.models import Index, Package
from myxa.resolver import Resolver


class TestResolver:
    def test_resolve_to_largest_minor_version(
        self,
        manager: Manager,
        resolver: Resolver,
        primary_index: Index,
        app_package: Package,
        euler_package: Package,
    ) -> None:
        manager.lock(euler_package, primary_index)
        manager.publish(euler_package, primary_index, interactive=False)
        manager.add(app_package, euler_package.info.name, primary_index, euler_package.info.version)

        manager.publish(euler_package, primary_index, interactive=False)
        new_version = euler_package.info.version

        lock = resolver.resolve(app_package)
        assert lock.deps[euler_package.info.name].version == new_version
        assert len(lock.deps) == 1

    def test_resolve_below_next_major_version(
        self,
        manager: Manager,
        resolver: Resolver,
        primary_index: Index,
        app_package: Package,
        euler_package: Package,
    ) -> None:
        original_version = euler_package.info.version
        manager.lock(euler_package, primary_index)
        manager.publish(euler_package, primary_index, interactive=False)
        manager.add(app_package, euler_package.info.name, primary_index, euler_package.info.version)

        manager.publish(euler_package, primary_index, interactive=False, major=True)

        lock = resolver.resolve(app_package)
        assert lock.deps[euler_package.info.name].version == original_version
        assert len(lock.deps) == 1

    def test_resolve_incompatible_deps_raises_user_error(  # noqa: PLR0913
        self,
        manager: Manager,
        resolver: Resolver,
        primary_index: Index,
        app_package: Package,
        interlet_package: Package,
        flatty_package: Package,
    ) -> None:
        manager.lock(flatty_package, primary_index)
        manager.publish(flatty_package, primary_index, interactive=False)
        manager.add(interlet_package, flatty_package.info.name, primary_index, flatty_package.info.version)

        manager.lock(interlet_package, primary_index)
        manager.publish(interlet_package, primary_index, interactive=False)
        manager.add(app_package, interlet_package.info.name, primary_index, interlet_package.info.version)

        manager.publish(flatty_package, primary_index, interactive=False, major=True)

        manager.add(app_package, flatty_package.info.name, primary_index, flatty_package.info.version)

        with pytest.raises(UserError, match="Failed to resolve package dependencies, no valid configuration found"):
            resolver.resolve(app_package)

    def test_ecosystem(  # noqa: PLR0913
        self,
        manager: Manager,
        resolver: Resolver,
        primary_index: Index,
        app_package: Package,
        euler_package: Package,
        interlet_package: Package,
        flatty_package: Package,
    ) -> None:
        manager.lock(euler_package, primary_index)
        manager.publish(euler_package, primary_index, interactive=False)
        manager.add(app_package, euler_package.info.name, primary_index, euler_package.info.version)

        manager.lock(flatty_package, primary_index)
        manager.publish(flatty_package, primary_index, interactive=False)
        manager.add(interlet_package, flatty_package.info.name, primary_index, flatty_package.info.version)

        manager.lock(interlet_package, primary_index)
        manager.publish(interlet_package, primary_index, interactive=False)
        manager.add(app_package, interlet_package.info.name, primary_index, interlet_package.info.version)

        lock = resolver.resolve(app_package)
        assert len(lock.deps) == 3
        for package in [euler_package, flatty_package, interlet_package]:
            assert lock.deps[package.info.name].version == package.info.version
