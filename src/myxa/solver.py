import logging
from dataclasses import dataclass
from typing import Iterator, Optional

from myxa.dependency import Dependency
from myxa.errors import UserError
from myxa.index import Index
from myxa.package import Lock, Package

logger = logging.getLogger(__name__)


@dataclass
class Pair:
    parent: Package
    dependency: Dependency


@dataclass(kw_only=True)
class Solver:
    index: Index

    def solve(self, package: Package) -> Optional[Lock]:
        init_lock = Lock()
        dependencies = package.dependencies.list()
        pairs = [Pair(package, dependency) for dependency in dependencies]
        locks = self._solve(pairs, init_lock)
        lock = next(locks, None)

        if lock is None:
            msg = "Failed to solve package dependencies, no valid configuration found"
            raise UserError(msg)

        if lock.has(package.info.name):
            lock.remove(package.info.name)
        return lock

    def _solve(self, pairs: list[Pair], lock: Lock) -> Iterator[Lock]:
        if len(pairs) == 0:
            yield lock
            return

        pair, *tail = pairs
        parent, dependency = pair.parent, pair.dependency
        if pin := lock.get(dependency.name):
            if dependency.is_satisfied_by(pin.version):
                yield from self._solve(tail, lock)
            return
        for package in self.index.list_versions_sorted(dependency.name):
            if not dependency.is_satisfied_by(package.info.version):
                continue
            if not lock.is_compatible_with(package):
                continue

            new_lock = lock.clone_add(package.to_pin(), parent_name=parent.info.name, source_name=self.index.name)
            dependency_pairs = [Pair(package, dep) for dep in package.dependencies.list()]
            new_dependencies = tail + dependency_pairs
            yield from self._solve(new_dependencies, new_lock)
