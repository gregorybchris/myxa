import json
import logging
from dataclasses import dataclass
from pathlib import Path

import inflect

from myxa.errors import UserError
from myxa.models import Dep, Index, Namespace, Package, PackageInfo, PackageLock, Version
from myxa.printer import Printer

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class Manager:
    printer: Printer
    inflect_engine: inflect.engine

    def init(self, name: str, description: str, package_filepath: Path) -> None:
        self.printer.print_message(f"Initializing package {name}...")
        if package_filepath.exists():
            msg = f"Package file already exists at {package_filepath.absolute()}"
            raise UserError(msg)

        package = Package(
            info=PackageInfo(name=name, description=description, version=Version(major=0, minor=1)),
            members={},
        )
        self.save_package(package, package_filepath)
        self.printer.print_success(f"Initialized {name} with package file at {package_filepath.absolute()}")

    def publish(self, package: Package, index: Index) -> None:
        self.printer.print_message(
            f"Publishing package {package.info.name} version {package.info.version.to_str()} to index {index.name}..."
        )
        if package.lock is None:
            msg = f"No lock found for package {package.info.name}, unable to publish it to index {index.name}"
            raise UserError(msg)

        # TODO: Check package name is valid with regex
        # TODO: Check that the version is incremented only by one (minor or major), should not skip a major or minor
        # TODO: Check that the info hasn't been updated more recently than the lock
        # TODO: Check that all dependencies at the correct versions exist in the index being published to

        info = package.info
        if namespace := index.namespaces.get(info.name):
            # TODO: Check that if this package correctly increments major version if changes are breaking
            if info.version.to_str() in namespace.packages:
                msg = f"Package {info.name} version {info.version.to_str()} already exists in index {index.name}"
                raise UserError(msg)
            namespace.packages[info.version.to_str()] = package
        else:
            namespace = Namespace(name=info.name)
            namespace.packages[info.version.to_str()] = package
            index.namespaces[info.name] = namespace
        self.printer.print_success(f"Published {info.name} version {info.version.to_str()} to index {index.name}")

    def _find_namespace(self, name: str, index: Index) -> Namespace:
        if namespace := index.namespaces.get(name):
            return namespace
        msg = f"Package {name} not found in the provided index: {index.name}"
        raise UserError(msg)

    def _get_latest_package(self, namespace: Namespace) -> Package:
        versions = [Version.from_str(s) for s in namespace.packages]
        latest_version = max(versions, key=lambda v: (v.major, v.minor))
        return namespace.packages[latest_version.to_str()]

    def add(self, package: Package, dep_name: str, index: Index) -> None:
        self.printer.print_message(f"Adding dependency {dep_name} to package {package.info.name}...")
        if package.info.deps.get(dep_name):
            msg = f"{dep_name} is already a dependency of {package.info.name}"
            raise UserError(msg)

        # TODO: Resolve the latest compatible version of the dep
        namespace = self._find_namespace(dep_name, index)
        latest_package = self._get_latest_package(namespace)
        version = latest_package.info.version
        package.info.deps[dep_name] = Dep(name=dep_name, version=version)
        self.printer.print_success(f"Added {dep_name}~={version.to_str()} to {package.info.name}")

    def remove(self, package: Package, dep_name: str) -> None:
        self.printer.print_message(f"Removing dependency {dep_name} from package {package.info.name}...")
        if dep := package.info.deps.pop(dep_name, None):
            self.printer.print_success(f"Removed {dep.name} from {package.info.name}")
        else:
            msg = f"{dep_name} is not a dependency of {package.info.name}, unable to remove it"
            raise UserError(msg)

    def lock(self, package: Package, index: Index) -> None:  # noqa: ARG002
        self.printer.print_message(f"Locking package {package.info.name}...")
        new_lock = PackageLock()
        # TODO: Resolve the latest compatible version of each dep
        for dep in package.info.deps.values():
            new_lock.deps[dep.name] = dep
        package.lock = new_lock
        n_deps = len(new_lock.deps)
        self.printer.print_success(
            f"Locked {package.info.name} with {n_deps} {self.inflect_engine.plural_noun('dependency', n_deps)}"
        )

    def update(self, package: Package) -> None:
        raise NotImplementedError

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
