from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Iterator, Optional, Self

Name = str


@dataclass
class Version:
    major: int
    minor: int

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclass
class Dependency:
    name: Name
    version: Version

    def is_satisfied_by(self, version: Version) -> bool:
        return version.major == self.version.major and version.minor >= self.version.minor

    def __str__(self) -> str:
        return f"{self.name}~={self.version}"


@dataclass
class Assignment:
    name: Name
    version: Version

    def __str__(self) -> str:
        return f"{self.name}=={self.version}"


@dataclass
class Package:
    name: Name
    version: Version
    dependencies: list[Dependency] = field(default_factory=list)

    def to_assignment(self) -> Assignment:
        return Assignment(name=self.name, version=self.version)

    def list_dependencies(self) -> list[Dependency]:
        return self.dependencies

    def __str__(self) -> str:
        return f"{self.name}=={self.version}"


@dataclass(kw_only=True)
class Index:
    packages: dict[Name, dict[Version, Package]] = field(default_factory=dict)

    def add(self, package: Package) -> None:
        if package.name not in self.packages:
            self.packages[package.name] = {}
        self.packages[package.name][package.version] = package

    def iter_versions_sorted(self, name: Name) -> Iterator[Package]:
        return iter(reversed(self.packages[name].values()))


@dataclass(kw_only=True)
class Solution:
    assignments: dict[Name, Assignment] = field(default_factory=dict)

    @classmethod
    def new(cls, assignments: list[Assignment]) -> Self:
        return cls(assignments={assignment.name: assignment for assignment in assignments})

    def has(self, name: Name) -> bool:
        return name in self.assignments

    def get(self, name: Name) -> Optional[Assignment]:
        return self.assignments.get(name)

    def iter(self) -> Iterator[Assignment]:
        return iter(self.assignments.values())

    def add(self, assignment: Assignment) -> None:
        self.assignments[assignment.name] = assignment

    def remove(self, name: Name) -> None:
        del self.assignments[name]

    def clone_add(self, assignment: Assignment) -> Solution:
        new_solution = deepcopy(self)
        new_solution.add(assignment)
        return new_solution

    def is_compatible_with(self, package: Package) -> bool:
        if assignment := self.get(package.name):  # noqa: SIM102
            if assignment.version != package.version:
                return False

        return True

    def __str__(self) -> str:
        if len(self.assignments) == 0:
            return "<empty>"
        return "<" + ", ".join(str(assignment) for assignment in self.iter()) + ">"


@dataclass(kw_only=True)
class Solver:
    index: Index

    def solve(self, package: Package) -> Optional[Solution]:
        init_solution = Solution()
        dependencies = package.list_dependencies()
        solutions = self._solve(dependencies, init_solution)
        solution = next(solutions, None)
        if solution is not None and solution.has(package.name):
            solution.remove(package.name)
        return solution

    def _solve(self, dependencies: list[Dependency], solution: Solution) -> Iterator[Solution]:
        if len(dependencies) == 0:
            yield solution
            return

        dependency, *rest = dependencies
        if assignment := solution.get(dependency.name):
            if dependency.is_satisfied_by(assignment.version):
                yield from self._solve(rest, solution)
            return
        for package in self.index.iter_versions_sorted(dependency.name):
            if not dependency.is_satisfied_by(package.version):
                continue
            if not solution.is_compatible_with(package):
                continue

            new_solution = solution.clone_add(package.to_assignment())
            new_dependencies = rest + package.list_dependencies()
            yield from self._solve(new_dependencies, new_solution)
