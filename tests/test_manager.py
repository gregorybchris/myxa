import re

import inflect
import pytest
from rich.console import Console

from myxa.errors import UserError
from myxa.manager import Manager
from myxa.models import Index, Package
from myxa.printer import Printer


@pytest.fixture(scope="module", name="manager")
def manager_fixture() -> Manager:
    console = Console()
    printer = Printer(console=console)
    inflect_engine = inflect.engine()
    return Manager(printer=printer, inflect_engine=inflect_engine)


class TestManager:
    def test_init(
        self,
        manager: Manager,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        package_dirpath = tmp_path_factory.mktemp("package")
        package_filepath = package_dirpath / "package.json"
        manager.init("myxa", "Compatibility aware package manager", package_filepath)
        package = manager.load_package(package_filepath)
        assert package.info.name == "myxa"
        assert package.info.description == "Compatibility aware package manager"
        assert len(package.info.deps) == 0
        assert package.lock is None

    def test_init_package_twice_raises_user_error(
        self,
        manager: Manager,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        package_dirpath = tmp_path_factory.mktemp("package")
        package_filepath = package_dirpath / "package.json"
        manager.init("myxa", "Compatibility aware package manager", package_filepath)
        with pytest.raises(UserError, match="Package file already exists at"):
            manager.init("myxa", "Compatibility aware package manager", package_filepath)

    def test_print_package_without_lock_raises_user_error(
        self,
        manager: Manager,
        euler_package: Package,
    ) -> None:
        with pytest.raises(UserError, match="No lock found for package euler"):
            manager.printer.print_package(euler_package, show_lock=True)

    def test_publish_without_lock_raises_user_error(
        self,
        manager: Manager,
        euler_package: Package,
        primary_index: Index,
    ) -> None:
        with pytest.raises(UserError, match="No lock found for package euler"):
            manager.publish(euler_package, primary_index)

    def test_publish_duplicate_version_raises_user_error(
        self,
        manager: Manager,
        euler_package: Package,
        primary_index: Index,
    ) -> None:
        manager.lock(euler_package, primary_index)
        manager.publish(euler_package, primary_index)
        with pytest.raises(UserError, match="Package euler version 0.1 already exists in index primary"):
            manager.publish(euler_package, primary_index)

    def test_package_not_found_in_index_raises_user_error(
        self,
        manager: Manager,
        primary_index: Index,
    ) -> None:
        with pytest.raises(UserError, match=re.escape("Package euler not found in the provided index: primary")):
            manager._find_namespace("euler", primary_index)

    def test_add(
        self,
        manager: Manager,
        interlet_package: Package,
        flatty_package: Package,
        primary_index: Index,
    ) -> None:
        manager.lock(flatty_package, primary_index)
        manager.publish(flatty_package, primary_index)
        assert "flatty" not in interlet_package.info.deps
        manager.add(interlet_package, "flatty", primary_index)
        assert "flatty" in interlet_package.info.deps

    def test_add_dependency_twice_raises_user_error(
        self,
        manager: Manager,
        interlet_package: Package,
        flatty_package: Package,
        primary_index: Index,
    ) -> None:
        manager.lock(flatty_package, primary_index)
        manager.publish(flatty_package, primary_index)
        manager.add(interlet_package, "flatty", primary_index)
        with pytest.raises(UserError, match="flatty is already a dependency of interlet"):
            manager.add(interlet_package, "flatty", primary_index)

    def test_remove(
        self,
        manager: Manager,
        interlet_package: Package,
        flatty_package: Package,
        primary_index: Index,
    ) -> None:
        manager.lock(flatty_package, primary_index)
        manager.publish(flatty_package, primary_index)
        manager.add(interlet_package, "flatty", primary_index)
        assert "flatty" in interlet_package.info.deps
        manager.remove(interlet_package, "flatty")
        assert "flatty" not in interlet_package.info.deps

    def test_remove_missing_dependency_raises_user_error(
        self,
        manager: Manager,
        interlet_package: Package,
    ) -> None:
        with pytest.raises(UserError, match="flatty is not a dependency of interlet, unable to remove it"):
            manager.remove(interlet_package, "flatty")

    def test_publish(
        self,
        manager: Manager,
        euler_package: Package,
        primary_index: Index,
    ) -> None:
        manager.lock(euler_package, primary_index)
        assert "euler" not in primary_index.namespaces
        manager.publish(euler_package, primary_index)
        assert "euler" in primary_index.namespaces

    def test_publish_multiple_versions(
        self,
        manager: Manager,
        euler_package: Package,
        primary_index: Index,
    ) -> None:
        manager.lock(euler_package, primary_index)
        manager.publish(euler_package, primary_index)
        assert "euler" in primary_index.namespaces
        assert "0.1" in primary_index.namespaces["euler"].packages
        euler_package.info.version.minor += 1
        manager.lock(euler_package, primary_index)
        manager.publish(euler_package, primary_index)
        assert "euler" in primary_index.namespaces
        assert "0.2" in primary_index.namespaces["euler"].packages

    def test_lock(
        self,
        manager: Manager,
        euler_package: Package,
        primary_index: Index,
    ) -> None:
        # NOTE: Need to assign the lock here so type checker doesn't complain
        lock = euler_package.lock
        assert lock is None
        manager.lock(euler_package, primary_index)
        lock = euler_package.lock
        assert lock is not None
        assert all(dep.name in lock.deps is not None for dep in euler_package.info.deps.values())

    def test_save_and_load_package_from_file(
        self,
        manager: Manager,
        app_package: Package,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        package_dirpath = tmp_path_factory.mktemp("package")
        package_filepath = package_dirpath / "package.json"
        manager.save_package(app_package, package_filepath)
        loaded_app_package = manager.load_package(package_filepath)
        assert app_package == loaded_app_package

    def test_save_and_load_index_from_file(
        self,
        manager: Manager,
        primary_index: Index,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        package_dirpath = tmp_path_factory.mktemp("package")
        primary_index_filepath = package_dirpath / "primary_index.json"
        manager.save_index(primary_index, primary_index_filepath)
        loaded_primary_index = manager.load_index(primary_index_filepath)
        assert primary_index == loaded_primary_index

    def test_ecosystem(  # noqa: PLR0913
        self,
        manager: Manager,
        euler_package: Package,
        flatty_package: Package,
        interlet_package: Package,
        app_package: Package,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        packages_dirpath = tmp_path_factory.mktemp("packages")
        euler_package_filepath = packages_dirpath / "euler.json"
        flatty_package_filepath = packages_dirpath / "flatty.json"
        interlet_package_filepath = packages_dirpath / "interlet.json"
        app_package_filepath = packages_dirpath / "app.json"
        primary_index_filepath = packages_dirpath / "primary_index.json"

        primary_index = Index(name="primary")

        manager.lock(euler_package, primary_index)
        manager.publish(euler_package, primary_index)

        manager.lock(flatty_package, primary_index)
        manager.publish(flatty_package, primary_index)

        manager.add(interlet_package, flatty_package.info.name, primary_index)
        manager.lock(interlet_package, primary_index)
        manager.publish(interlet_package, primary_index)

        manager.add(app_package, euler_package.info.name, primary_index)
        manager.add(app_package, interlet_package.info.name, primary_index)
        manager.lock(app_package, primary_index)

        manager.save_package(euler_package, euler_package_filepath)
        manager.save_package(flatty_package, flatty_package_filepath)
        manager.save_package(interlet_package, interlet_package_filepath)
        manager.save_package(app_package, app_package_filepath)

        manager.save_index(primary_index, primary_index_filepath)
        primary_index = manager.load_index(primary_index_filepath)
