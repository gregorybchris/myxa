import logging
from dataclasses import dataclass, field
from enum import StrEnum, auto

logger = logging.getLogger(__name__)


class Type(StrEnum):
    Str = auto()
    Int = auto()
    Float = auto()
    Bool = auto()


@dataclass(kw_only=True)
class Node:
    pass


@dataclass
class Param(Node):
    name: str
    type: Type
    has_default: bool = False


@dataclass(kw_only=True)
class Func(Node):
    name: str
    params: dict[str, Param]
    return_type: Type


@dataclass(kw_only=True)
class ImportPath(Node):
    module_names: list[str]
    member_name: str


@dataclass(kw_only=True)
class Mod(Node):
    name: str
    imports: list[ImportPath]
    members: dict[str, Node]


@dataclass(kw_only=True)
class Version:
    alpha: int
    beta: int


@dataclass(kw_only=True)
class Dependency:
    name: str
    version: Version


@dataclass(kw_only=True)
class PackageLock:
    dependencies: dict[str, Dependency]


@dataclass(kw_only=True)
class PackageDefinition:
    name: str
    description: str
    version: Version
    dependencies: dict[str, str]


@dataclass(kw_only=True)
class Package:
    definition: PackageDefinition
    lock: PackageLock
    modules: list[Mod]


@dataclass(kw_only=True)
class Repository:
    packages: dict[str, Package] = field(default_factory=dict)


@dataclass(kw_only=True)
class Manager:
    repository: Repository

    def lock(self, package: Package) -> None:
        raise NotImplementedError

    def publish(self, package: Package) -> None:
        raise NotImplementedError

    def add(self, package: Package, dependency: Dependency) -> None:
        raise NotImplementedError

    def update(self, package: Package) -> None:
        raise NotImplementedError


def main() -> None:
    repository = Repository()
    manager = Manager(repository=repository)

    add_function = Func(
        name="add",
        params={
            "a": Param("a", Type.Int),
            "b": Param("b", Type.Int),
        },
        return_type=Type.Int,
    )

    math_module = Mod(
        name="math",
        imports=[],
        members={
            "add": add_function,
        },
    )

    euler_package = Package(
        definition=PackageDefinition(
            name="euler",
            description="A package for math functions",
            version=Version(alpha=0, beta=1),
            dependencies={},
        ),
        lock=PackageLock(dependencies={}),
        modules=[math_module],
    )

    print(euler_package)

    manager.publish(euler_package)
