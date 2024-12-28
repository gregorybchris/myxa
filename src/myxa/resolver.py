import logging
from dataclasses import dataclass, field
from typing import Iterator, Optional

from myxa.errors import UserError
from myxa.models import Dep, Index, Namespace, Package, Version

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class Resolver:
    index: Index

    resolved: dict[str, Dep] = field(default_factory=dict)
    seen: set[str] = field(default_factory=set)
    entry_package: Optional[Package] = None

    def resolve(self, entry_package: Package) -> dict[str, Dep]:
        self.entry_package = entry_package
        if not self._resolve(entry_package):
            msg = "Unable to resolve dependencies."
            raise UserError(msg)
            # TODO: Add a test for this case
        self.resolved.pop(entry_package.info.name)
        ret = self.resolved
        self.resolved = {}
        return ret

    def get_namespace(self, package_name: str) -> Namespace:
        if namespace := self.index.namespaces.get(package_name):
            return namespace
        msg = f"{package_name} not found in index {self.index.name}"
        raise UserError(msg)

    def iter_namespace(self, package_name: str) -> Iterator[Package]:
        namespace = self.get_namespace(package_name)
        yield from namespace.packages.values()

    def iter_versions(self, package_name: str) -> Iterator[Version]:
        for package in self.iter_namespace(package_name):
            yield package.info.version

    def get_package(self, package_name: str, version: Version) -> Package:
        namespace = self.get_namespace(package_name)
        if package := namespace.packages.get(version.to_str()):
            return package
        msg = f"{package_name} version {version.to_str()} not found in index {self.index.name}"
        raise UserError(msg)

    def iter_package_versions(self, package: Package) -> Iterator[Version]:
        # Avoid looking up entry package in index
        if self.entry_package is not None and package.info.name == self.entry_package.info.name:
            yield self.entry_package.info.version
            return

        package_versions = (Version.from_str(s) for s in self.index.namespaces[package.info.name].packages)
        # Try highest version first
        for version in sorted(package_versions, reverse=True):
            yield version

    def _resolve(self, package: Package) -> bool:
        package_name = package.info.name

        if package_name in self.resolved:
            return True  # Already resolved

        if package_name in self.seen:
            return False  # Cycle detected
        self.seen.add(package_name)

        for version in self.iter_package_versions(package):
            self.resolved[package_name] = Dep(name=package_name, version=version)
            logger.debug("Trying %s version %s", package_name, version.to_str())

            satisfied = True

            # TODO: Sort deps by something like the one with the most dependencies first
            for dep in package.info.deps.values():
                if dep.name not in self.index.namespaces:
                    msg = f"Dependency {dep.name} not found in index {self.index.name}"
                    raise UserError(msg)

                dep_package = self.index.namespaces[dep.name].packages[dep.version.to_str()]

                if not self._resolve(dep_package):
                    satisfied = False
                    break
                if not self.satisfies(self.resolved[dep.name].version, dep):
                    satisfied = False
                    break

            if satisfied:
                return True

            logger.debug("Backtracking %s version %s", package_name, version.to_str())
            self.resolved.pop(package_name)

        self.seen.remove(package_name)
        return False

    @classmethod
    def satisfies(cls, version: Version, dep: Dep) -> bool:
        dep_version = dep.version
        if version.major != dep_version.major:
            return False
        return version.minor >= dep_version.minor
