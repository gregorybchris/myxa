import logging
from dataclasses import dataclass
from itertools import product
from typing import Iterator

from myxa.errors import UserError
from myxa.models import Dep, Index, Package, PackageLock, Version

logger = logging.getLogger(__name__)


Name = str
VerStr = str
FlatDeps = dict[Name, dict[VerStr, dict[Name, VerStr]]]
VersionsMap = dict[Name, list[VerStr]]
Result = dict[Name, VerStr]


@dataclass(kw_only=True)
class Resolver:
    index: Index

    def resolve(self, package: Package) -> PackageLock:
        flat_deps: FlatDeps = {}
        self._fill_flat_deps(package, flat_deps)

        # The root package is required to satisfy all of its dependencies
        flat_deps[package.info.name] = {}
        flat_deps[package.info.name][package.info.version.to_str()] = {}
        for dep_name, dep in package.info.deps.items():
            flat_deps[package.info.name][package.info.version.to_str()][dep_name] = dep.version.to_str()

        versions_map = self._get_versions_map(flat_deps)

        for candidate in self._iter_candidates(versions_map):
            if self._satisfies_all(candidate, flat_deps):
                # Remove the root package from the candidate set. It's not a dependency of itself
                candidate.pop(package.info.name)
                return self._create_lock(candidate)

        msg = "Failed to resolve package dependencies, no valid configuration found"
        raise UserError(msg)

    def _create_lock(self, candidate: Result) -> PackageLock:
        deps = {}
        for name, version in candidate.items():
            dep = Dep(name=name, version=Version.from_str(version))
            deps[name] = dep
        return PackageLock(deps=deps)

    def _fill_flat_deps(self, package: Package, flat_deps: FlatDeps) -> None:
        for dep_name, _ in package.info.deps.items():
            flat_deps[dep_name] = {}
            sorted_versions = sorted(self.index.list_versions(dep_name), reverse=True)
            for dep_version in sorted_versions:
                verstr = dep_version.to_str()
                flat_deps[dep_name][verstr] = {}
                dep_package = self.index.get_package(dep_name, dep_version)
                for sub_dep_name, sub_dep in dep_package.info.deps.items():
                    sub_dep_verstr = sub_dep.version.to_str()
                    flat_deps[dep_name][verstr][sub_dep_name] = sub_dep_verstr
                self._fill_flat_deps(dep_package, flat_deps)

    def _get_versions_map(self, flat_deps: FlatDeps) -> VersionsMap:
        versions_map = {}
        for name, versions in flat_deps.items():
            versions_map[name] = list(versions.keys())
        return versions_map

    def _iter_candidates(self, versions_map: VersionsMap) -> Iterator[Result]:
        for versions in product(*versions_map.values()):
            result = dict(zip(versions_map.keys(), versions, strict=False))
            yield result

    def _satisfies_all(self, candidate: Result, flat_deps: FlatDeps) -> bool:
        for name_a, version_a in candidate.items():
            for name_b, version_b in candidate.items():
                if name_a == name_b:
                    continue
                constraints_a = flat_deps[name_a][version_a]
                constraints_b = flat_deps[name_b][version_b]
                if name_a in constraints_b and not self._satisfies(version_a, constraints_b[name_a]):
                    return False
                if name_b in constraints_a and not self._satisfies(version_b, constraints_a[name_b]):
                    return False
        return True

    @classmethod
    def _satisfies(cls, result_version: str, dep_version: str) -> bool:
        result_ver = Version.from_str(result_version)
        dep_ver = Version.from_str(dep_version)
        if result_ver.major != dep_ver.major:
            return False
        return result_ver.minor >= dep_ver.minor
