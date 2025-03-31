import logging
from dataclasses import dataclass
from typing import Iterator, Optional

from myxa.dependency import Dependency
from myxa.errors import UserError
from myxa.index import Index
from myxa.package import Lock, Package

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class Solver:
    index: Index

    def solve(self, package: Package) -> Optional[Lock]:
        init_lock = Lock()
        dependencies = package.dependencies.list()
        locks = self._solve(dependencies, init_lock)
        lock = next(locks, None)

        if lock is None:
            msg = "Failed to solve package dependencies, no valid configuration found"
            raise UserError(msg)

        if lock.has(package.info.name):
            lock.remove(package.info.name)
        return lock

    def _solve(self, dependencies: list[Dependency], lock: Lock) -> Iterator[Lock]:
        if len(dependencies) == 0:
            yield lock
            return

        dependency, *rest = dependencies
        if pin := lock.get(dependency.name):
            if dependency.is_satisfied_by(pin.version):
                yield from self._solve(rest, lock)
            return
        for package in self.index.list_versions_sorted(dependency.name):
            if not dependency.is_satisfied_by(package.info.version):
                continue
            if not lock.is_compatible_with(package):
                continue

            new_lock = lock.clone_add(package.to_pin())
            new_dependencies = rest + package.dependencies.list()
            yield from self._solve(new_dependencies, new_lock)
