import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import inflect

from myxa.checker import Checker
from myxa.errors import UserError
from myxa.extra_types import Pluralizer
from myxa.models import Dep, Index, Package, PackageInfo, Version
from myxa.printer import Printer
from myxa.resolver import Resolver

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class Manager:
    printer: Printer = field(default_factory=Printer)
    pluralizer: Pluralizer = field(default_factory=inflect.engine)

    def init(self, name: str, description: str, package_filepath: Path) -> None:
        self.printer.print_message(f"Initializing package {name} :smiley:")
        if package_filepath.exists():
            msg = f"Package file already exists at {package_filepath.absolute()}"
            raise UserError(msg)

        package = Package(
            info=PackageInfo(
                name=name,
                description=description,
                version=Version.default(),
                deps={},
            ),
            members={},
        )
        self.save_package(package, package_filepath)
        self.printer.print_success(f"Initialized {name} with package file at {package_filepath.absolute()}")

    def info(  # noqa: PLR0913
        self,
        package: Package,
        index: Index,
        version: Optional[Version] = None,
        show_deps: bool = True,
        show_lock: bool = True,
        show_interface: bool = True,
    ) -> None:
        if version is not None and version != package.info.version:
            package = index.get_package(package.info.name, version)
        self.printer.print_package(
            package,
            show_deps=show_deps,
            show_lock=show_lock,
            show_interface=show_interface,
        )

    def add(self, package: Package, dep_name: str, index: Index, version: Optional[Version] = None) -> None:
        self.printer.print_message(f"Adding dependency {dep_name} to package {package.info.name}...")
        if package.info.deps.get(dep_name) and (version is None or package.info.deps[dep_name].version == version):
            msg = f"{dep_name} is already a dependency of {package.info.name}"
            raise UserError(msg)

        # TODO: Add the latest compatible version if version not provided, not just the latest version
        # TODO: Check that the provided version is compatible before adding it
        if version is None:
            dep_package = index.get_latest_package(dep_name)
            version = dep_package.info.version
        package.info.deps[dep_name] = Dep(name=dep_name, version=version)
        self.printer.print_success(f"Added {dep_name}~={version.to_str()} to {package.info.name}")

    def remove(self, package: Package, dep_name: str) -> None:
        self.printer.print_message(f"Removing dependency {dep_name} from package {package.info.name}...")
        if dep := package.info.deps.pop(dep_name, None):
            self.printer.print_success(f"Removed {dep.name} from {package.info.name}")
        else:
            msg = f"{dep_name} is not a dependency of {package.info.name}, unable to remove it"
            raise UserError(msg)

    def lock(self, package: Package, index: Index) -> None:
        self.printer.print_message(f"Locking package {package.info.name}...")
        old_lock = package.lock
        # Check that all dependencies exist in the index before trying to resolve
        for dep in package.info.deps.values():
            index.get_package(dep.name, dep.version)
        resolver = Resolver(index=index)
        package.lock = resolver.resolve(package)
        self.printer.print_lock_diff(old_lock, package.lock)

    def unlock(self, package: Package) -> None:
        self.printer.print_message(f"Unlocking package {package.info.name}...")
        if package.lock is None:
            msg = f"No lock found for package {package.info.name}, unable to remove lock"
            raise UserError(msg)
        n_deps = len(package.lock.deps)
        package.lock = None
        self.printer.print_success(
            f"Unlocked {package.info.name} with {n_deps} {self.pluralizer.plural_noun('dependency', n_deps)}"
        )

    def update(self, package: Package, index: Index) -> None:
        self.printer.print_message(f"Updating dependencies for {package.info.name}...")
        old_lock = package.lock
        # Check that all dependencies exist in the index before trying to resolve
        for dep in package.info.deps.values():
            index.get_package(dep.name, dep.version)
        resolver = Resolver(index=index)
        package.lock = resolver.resolve(package)
        self.printer.print_lock_diff(old_lock, package.lock)

    def check(self, package: Package, index: Index) -> None:
        self.printer.print_message(f"Checking package {package.info.name}...")
        checker = Checker()
        latest_package = index.get_latest_package(package.info.name)
        compat_breaks = checker.check(latest_package, package)
        if len(compat_breaks) > 0:
            self.printer.print_breaks(compat_breaks, latest_package)
        else:
            self.printer.print_success("No compatibility breaks found")

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
            latest_package = index.get_latest_package(package.info.name)
            latest_version = latest_package.info.version

            self.printer.print_message(
                f"The latest published version of {package.info.name} is {latest_version.to_str()}"
            )

            checker = Checker()
            compat_breaks = checker.check(latest_package, package)
            if len(compat_breaks) > 0:
                self.printer.print_breaks(compat_breaks, latest_package)
                candidate_version = latest_version.next_major()
                self.printer.print_warning(f"Will increment the major version to {candidate_version.to_str()}")
            elif major:
                candidate_version = latest_version.next_major()
                self.printer.print_message(
                    f"Major flag set. Will increment the major version to {candidate_version.to_str()}"
                )
            else:
                candidate_version = latest_version.next_minor()
                self.printer.print_message(f"Will increment the minor version to {candidate_version.to_str()}")
        except UserError:
            self.printer.print_message(
                f"Package {package.info.name} has not been published yet."
                f" The initial version will be set automatically to {Version.default().to_str()}"
            )
            candidate_version = Version.default()

        if interactive:
            while response := self.printer.input("Proceed to publish? \\[y/n] "):
                if response.lower() == "n":
                    self.printer.print_success("Successfully aborted publishing")
                    break
                if response.lower() == "y":
                    self.set_version(package, candidate_version)
                    index.add_package(package)
                    self.printer.print_success(
                        f"Published {package.info.name} version {candidate_version.to_str()} to index {index.name}"
                    )
                    break
        else:
            self.set_version(package, candidate_version)
            index.add_package(package)
            self.printer.print_success(
                f"Force published {package.info.name} version {candidate_version.to_str()} to index {index.name}"
            )

    def yank(self, package: Package, version: Version, index: Index) -> None:
        self.printer.print_message(f"Yanking package {package.info.name}...")
        index.remove_package(package, version)
        self.printer.print_success(f"Yanked {package.info.name} version {version.to_str()} from index {index.name}")

    def set_version(self, package: Package, version: Version) -> None:
        self.printer.print_message(f"Setting version of package {package.info.name} to {version.to_str()}...")
        package.info.version = version
        self.printer.print_success(f"Set version of {package.info.name} to {version.to_str()}")

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
