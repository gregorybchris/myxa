import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import inflect

from myxa.checker import Checker
from myxa.dependency import Dependency
from myxa.errors import UserError
from myxa.extra_types import Pluralizer
from myxa.index import Index
from myxa.package import Info, Package
from myxa.printer import Printer
from myxa.solver import Solver
from myxa.version import Version

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class Manager:
    printer: Printer = field(default_factory=Printer)
    pluralizer: Pluralizer = field(default_factory=inflect.engine)

    def init(
        self,
        package_filepath: Path,
        name: Optional[str] = None,
        description: Optional[str] = None,
        interactive: bool = True,
    ) -> None:
        if interactive:
            if name is None:
                while response := self.printer.input("Enter a package name: "):
                    # TODO: Check package name has allowed characters
                    if len(response) > 0:
                        name = response
                        break
            if description is None:
                while response := self.printer.input("Enter a description for the package: "):
                    if len(response) > 0:
                        description = response
                        break

        if name is None or description is None:
            msg = "Package name and description are required to initialize a new package"
            raise UserError(msg)

        if package_filepath.exists():
            msg = f"Package file already exists at {package_filepath.absolute()}"
            raise UserError(msg)

        self.printer.print_message(f"Initializing package {name} :smiley:")

        package = Package(
            info=Info(
                name=name,
                description=description,
                version=Version.default(),
            ),
            dependencies={},
            members={},
        )
        self.save_package(package, package_filepath)
        self.printer.print_success(f"Initialized {name} with package file at {package_filepath.absolute()}")

    def info(  # noqa: PLR0913
        self,
        package: Package,
        index: Index,
        version: Optional[Version] = None,
        show_dependencies: bool = True,
        show_lock: bool = True,
        show_members: bool = True,
    ) -> None:
        if version is not None and version != package.info.version:
            package = index.get(package.info.name, version)
        self.printer.print_package(
            package,
            show_dependencies=show_dependencies,
            show_lock=show_lock,
            show_members=show_members,
            index=index,
        )

    def add(self, package: Package, name: str, index: Index, version: Optional[Version] = None) -> None:
        self.printer.print_message(f"Adding dependency {name} to package {package.info.name}...")
        if dependency := package.dependencies.get(name):  # noqa: SIM102
            if version is None or dependency.version == version:
                msg = f"{name} is already a dependency of {package.info.name}"
                raise UserError(msg)

        # TODO: Add the latest compatible version if version not provided, not just the latest version
        # TODO: Check that the provided version is compatible before adding it
        if version is None:
            dependency_package = index.get_latest(name)
            version = dependency_package.info.version
        package.dependencies.add(Dependency(name=name, version=version))
        self.printer.print_success(f"Added {name}~={version} to {package.info.name}")

    def remove(self, package: Package, name: str) -> None:
        self.printer.print_message(f"Removing dependency {name} from package {package.info.name}...")
        if dependency := package.dependencies.pop(name):
            self.printer.print_success(f"Removed {dependency.name} from {package.info.name}")
        else:
            msg = f"{name} is not a dependency of {package.info.name}, unable to remove it"
            raise UserError(msg)

    def lock(self, package: Package, index: Index) -> None:
        self.printer.print_message(f"Locking package {package.info.name}...")
        old_lock = package.lock
        # Check that all dependencies exist in the index before trying to solve
        for dependency in package.dependencies.list():
            index.get(dependency.name, dependency.version)
        solver = Solver(index=index)
        lock = solver.solve(package)
        if lock is None:
            msg = f"No solution found for package {package.info.name} with current dependencies"
            raise UserError(msg)
        package.lock = lock
        self.printer.print_lock_diff(old_lock, package.lock)

    def unlock(self, package: Package) -> None:
        self.printer.print_message(f"Unlocking package {package.info.name}...")
        if package.lock is None:
            msg = f"No lock found for package {package.info.name}, unable to remove lock"
            raise UserError(msg)
        n_dependencies = len(package.lock)
        package.lock = None
        self.printer.print_success(
            f"Unlocked {package.info.name} with {n_dependencies}"
            f" {self.pluralizer.plural_noun('dependency', n_dependencies)}"
        )

    def update(self, package: Package, index: Index) -> None:
        self.printer.print_message(f"Updating dependencies for {package.info.name}...")
        old_lock = package.lock
        # Check that all dependencies exist in the index before trying to solve
        for dependency in package.dependencies.list():
            index.get(dependency.name, dependency.version)
        solver = Solver(index=index)
        lock = solver.solve(package)
        if lock is None:
            msg = f"No solution found for package {package.info.name} with current dependencies"
            raise UserError(msg)
        package.lock = lock
        self.printer.print_lock_diff(old_lock, package.lock)

    def check(self, package: Package, index: Index, version: Optional[Version] = None) -> None:
        self.printer.print_message(f"Checking package {package.info.name}...")
        if version is not None and version != package.info.version:
            comparison_package = index.get(package.info.name, version)
        else:
            comparison_package = index.get_latest(package.info.name)

        checker = Checker()
        changes = checker.diff(comparison_package, package)
        if len(changes) > 0:
            self.printer.print_changes(changes, comparison_package, breaking_only=True)
        else:
            self.printer.print_success("No compatibility breaks found")

    def diff(self, package: Package, index: Index, version: Optional[Version] = None) -> None:
        self.printer.print_message(f"Diffing package {package.info.name}...")
        if version is not None and version != package.info.version:
            comparison_package = index.get(package.info.name, version)
        else:
            comparison_package = index.get_latest(package.info.name)

        checker = Checker()
        changes = checker.diff(comparison_package, package)
        if len(changes) > 0:
            self.printer.print_changes(changes, comparison_package)
        else:
            self.printer.print_success("No changes found")

    def publish(
        self,
        package: Package,
        index: Index,
        interactive: bool = True,
        major: bool = False,
    ) -> None:
        self.printer.print_message(f"Publishing package {package.info.name} to index {index.name}...")
        if package.lock is None:
            msg = f"No lock found for package {package.info.name}, unable to publish it to index {index.name}"
            raise UserError(msg)

        if re.search(r"[^a-z-]", package.info.name):
            msg = "Package name must be lowercase and can only contain letters and hyphens"
            raise UserError(msg)

        if package.info.name.startswith("-") or package.info.name.endswith("-"):
            msg = "Package name cannot start or end with a hyphen"
            raise UserError(msg)

        # TODO: Check that the info hasn't been updated more recently than the lock
        # TODO: Check that all dependencies at the correct versions exist in the index being published to

        try:
            latest_package = index.get_latest(package.info.name)
            latest_version = latest_package.info.version

            self.printer.print_message(f"The latest published version of {package.info.name} is {latest_version!s}")

            checker = Checker()
            changes = checker.diff(latest_package, package)
            breaks = [change for change in changes if change.is_breaking()]
            if len(breaks) > 0:
                self.printer.print_changes(changes, latest_package, breaking_only=True)
                candidate_version = latest_version.next_major()
                self.printer.print_warning(f"Will increment the major version to {candidate_version!s}")
            elif major:
                candidate_version = latest_version.next_major()
                self.printer.print_message(f"Major flag set. Will increment the major version to {candidate_version!s}")
            else:
                candidate_version = latest_version.next_minor()
                self.printer.print_message(f"Will increment the minor version to {candidate_version!s}")
        except UserError:
            self.printer.print_message(
                f"Package {package.info.name} has not been published yet."
                f" The initial version will be set automatically to {Version.default()!s}"
            )
            candidate_version = Version.default()

        if interactive:
            while response := self.printer.input("Proceed to publish? \\[y/n] "):
                if response.lower() == "n":
                    self.printer.print_success("Successfully aborted publishing")
                    break
                if response.lower() == "y":
                    self.set_version(package, candidate_version)
                    index.add(package)
                    self.printer.print_success(
                        f"Published {package.info.name} version {candidate_version!s} to index {index.name}"
                    )
                    break
        else:
            self.set_version(package, candidate_version)
            index.add(package)
            self.printer.print_success(
                f"Force published {package.info.name} version {candidate_version!s} to index {index.name}"
            )

    def yank(
        self,
        package: Package,
        version: Version,
        index: Index,
        interactive: bool = True,
    ) -> None:
        self.printer.print_message(f"Yanking package {package.info.name}...")

        if interactive:
            while response := self.printer.input("Proceed to yank? \\[y/n] "):
                if response.lower() == "n":
                    self.printer.print_success("Successfully aborted yanking")
                    break
                if response.lower() == "y":
                    index.remove(package, version)
                    self.printer.print_success(
                        f"Yanked {package.info.name} version {version!s} from index {index.name}"
                    )
                    break
        else:
            index.remove(package, version)
            self.printer.print_success(f"Force yanked {package.info.name} version {version!s} from index {index.name}")

    def set_version(self, package: Package, version: Version) -> None:
        self.printer.print_message(f"Setting version of package {package.info.name} to {version!s}...")
        package.info.version = version
        self.printer.print_success(f"Set version of {package.info.name} to {version!s}")

    def load_package(self, package_filepath: Path) -> Package:
        if not package_filepath.exists():
            msg = f"Package file not found at {package_filepath}"
            raise UserError(msg)
        with package_filepath.open("r") as fp:
            package_dict = json.load(fp)
        return Package(**package_dict)

    def save_package(self, package: Package, package_filepath: Path) -> None:
        with package_filepath.open("w") as fp:
            fp.write(package.model_dump_json(indent=2))

    def load_index(self, index_filepath: Path) -> Index:
        if not index_filepath.exists():
            msg = f"Index file not found at {index_filepath}"
            raise UserError(msg)
        with index_filepath.open("r") as fp:
            index_dict = json.load(fp)
        return Index(**index_dict)

    def save_index(self, index: Index, index_filepath: Path) -> None:
        with index_filepath.open("w") as fp:
            fp.write(index.model_dump_json(indent=2))
