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
        self._resolve_package(entry_package)

        # Remove entry package because it's not a dependency of itself
        self.resolved.pop(entry_package.info.name)
        ret = self.resolved
        self.resolved = {}
        return ret

    def _get_namespace(self, package_name: str) -> Namespace:
        if namespace := self.index.namespaces.get(package_name):
            return namespace
        msg = f"{package_name} not found in index {self.index.name}"
        raise UserError(msg)

    def _iter_namespace(self, package_name: str) -> Iterator[Package]:
        namespace = self._get_namespace(package_name)
        yield from namespace.packages.values()

    def _iter_versions(self, package_name: str) -> Iterator[Version]:
        for package in self._iter_namespace(package_name):
            yield package.info.version

    def _get_package(self, package_name: str, version: Version) -> Package:
        namespace = self._get_namespace(package_name)
        if package := namespace.packages.get(version.to_str()):
            return package
        msg = f"{package_name} version {version.to_str()} not found in index {self.index.name}"
        raise UserError(msg)

    def _iter_package_versions(self, package: Package) -> Iterator[Version]:
        # Avoid looking up entry package in index
        if self.entry_package is not None and package.info.name == self.entry_package.info.name:
            yield self.entry_package.info.version
            return

        package_versions = self._iter_versions(package.info.name)
        # Try highest version first
        for version in sorted(package_versions, reverse=True):
            yield version

    def _resolve_package(self, package: Package) -> None:
        logger.debug("Resolving %s", package.info.name)
        package_name = package.info.name

        if package_name in self.resolved:
            return

        if package_name in self.seen:
            msg = f"Cycle detected: {package_name}"
            raise UserError(msg)
        self.seen.add(package_name)

        for package_version in self._iter_package_versions(package):
            logger.debug("Trying %s==%s", package_name, package_version.to_str())
            self.resolved[package_name] = Dep(name=package_name, version=package_version)

            if self._resolve_deps(package):
                return

            logger.debug("Backtracking because %s!=%s", package_name, package_version.to_str())
            self.resolved.pop(package_name)

        self.seen.remove(package_name)
        msg = f"Unable to resolve {package_name}"
        raise UserError(msg)

    def _resolve_deps(self, package: Package) -> bool:
        # TODO: Sort deps by how many versions they have, fewest first
        for dep in package.info.deps.values():
            logger.debug(
                "Checking dep %s==%s for %s==%s",
                dep.name,
                dep.version.to_str(),
                package.info.name,
                package.info.version.to_str(),
            )

            dep_package = self._get_package(dep.name, dep.version)
            self._resolve_package(dep_package)

            resolved_version = self.resolved[dep.name].version
            if not self.satisfies(resolved_version, dep):
                logger.debug(
                    "Dependency %s==%s does not satisfy %s~=%s",
                    dep.name,
                    resolved_version.to_str(),
                    dep.name,
                    dep.version.to_str(),
                )
                return False

        logger.debug("Resolved %s==%s", package.info.name, package.info.version.to_str())
        return True

    @classmethod
    def satisfies(cls, version: Version, dep: Dep) -> bool:
        dep_version = dep.version
        if version.major != dep_version.major:
            return False
        return version.minor >= dep_version.minor
