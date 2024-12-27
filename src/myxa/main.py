import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional

from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

logger = logging.getLogger(__name__)


class Type(StrEnum):
    Str = "Str"
    Int = "Int"
    Float = "Float"
    Bool = "Bool"


@dataclass(kw_only=True)
class Node:
    pass


@dataclass
class Param(Node):
    name: str
    type: Type


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


@dataclass(kw_only=True, frozen=True)
class Version:
    major: int
    minor: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclass(kw_only=True)
class Dep:
    name: str
    version: Version


@dataclass(kw_only=True)
class PackageLock:
    deps: dict[str, Dep] = field(default_factory=dict)


@dataclass(kw_only=True)
class PackageInfo:
    name: str
    description: str
    version: Version
    deps: dict[str, Dep] = field(default_factory=dict)


@dataclass(kw_only=True)
class Package:
    info: PackageInfo
    lock: Optional[PackageLock] = None
    modules: dict[str, Mod]


@dataclass(kw_only=True)
class Namespace:
    name: str
    packages: dict[Version, Package] = field(default_factory=dict)


@dataclass(kw_only=True)
class Index:
    name: str
    namespaces: dict[str, Namespace] = field(default_factory=dict)


@dataclass(kw_only=True)
class Manager:
    console: Console

    def publish(self, package: Package, index: Index) -> None:
        if package.lock is None:
            msg = f"No lock found for package {package.info.name}, unable to publish it to index {index.name}"
            raise ValueError(msg)

        # TODO: Check package name is valid with regex
        # TODO: Check that the version is incremented only by one (minor or major)

        info = package.info
        if namespace := index.namespaces.get(info.name):
            # TODO: Check that if this package correctly increments major version if changes are breaking
            if info.version in namespace.packages:
                msg = f"Package {info.name} version {info.version} already exists in index {index.name}"
                raise ValueError(msg)
            namespace.packages[info.version] = package
        else:
            namespace = Namespace(name=info.name)
            namespace.packages[info.version] = package
            index.namespaces[info.name] = namespace

    def _find_namespace(self, name: str, indexes: list[Index]) -> Namespace:
        for index in indexes:
            if namespace := index.namespaces.get(name):
                return namespace
        msg = f"Package {name} not found in any provided indexes"
        raise ValueError(msg)

    def _get_latest_package(self, namespace: Namespace) -> Package:
        versions = list(namespace.packages.keys())
        latest_version = max(versions, key=lambda v: (v.major, v.minor))
        return namespace.packages[latest_version]

    def add(self, package: Package, dep_name: str, indexes: list[Index]) -> None:
        if package.info.deps.get(dep_name):
            msg = f"{dep_name} is already a dependency of {package.info.name}"
            raise ValueError(msg)

        # TODO: Resolve the latest compatible version of the dep
        namespace = self._find_namespace(dep_name, indexes)
        latest_package = self._get_latest_package(namespace)
        version = latest_package.info.version
        dep = Dep(name=dep_name, version=version)
        package.info.deps[dep_name] = dep

    def lock(self, package: Package) -> None:
        new_lock = PackageLock()
        # TODO: Resolve the latest compatible version of each dep
        for dep in package.info.deps.values():
            new_lock.deps[dep.name] = dep
        package.lock = new_lock

    def update(self, package: Package) -> None:
        raise NotImplementedError

    def _add_mod_tree(self, mod: Mod, tree: Tree) -> None:
        mod_tree = tree.add(mod.name, style="steel_blue3")
        for member in mod.members.values():
            match member:
                case Mod(name=name):
                    self._add_mod_tree(member, mod_tree)
                case Func(name=name, params=params, return_type=return_type):
                    func_str = f"{name}("
                    for param_name, param in params.items():
                        func_str += f"{param_name}: {param.type}, "
                    func_str = func_str[:-2] + ")"
                    func_str += f" -> {return_type}"
                    mod_tree.add(func_str, style="steel_blue1")
                case _:
                    msg = f"Unexpected member type {type(member)}"
                    raise ValueError(msg)

    def print_package_info(self, package: Package, lock: bool = False, modules: bool = False) -> None:
        info = package.info

        table = Table(show_header=False, border_style="black")
        table.add_column("", style="steel_blue3")
        table.add_column("", style="steel_blue1")
        table.add_row("Name", info.name)
        table.add_row("Description", info.description)
        table.add_row("Version", str(info.version))

        deps_tree = Tree("Dependencies", style="steel_blue3")
        for dep in info.deps.values():
            deps_tree.add(f"{dep.name}~={dep.version}", style="steel_blue1")
        if not info.deps:
            deps_tree.add("\\[none]", style="steel_blue1")

        padding = Padding("")

        group_renderables: tuple = (table, padding, deps_tree)
        if lock:
            if package.lock is None:
                msg = f"No lock found for package {package.info.name}"
                raise ValueError(msg)

            lock_tree = Tree("Locked dependencies", style="steel_blue3")
            for dep in package.lock.deps.values():
                lock_tree.add(f"{dep.name}=={dep.version}", style="steel_blue1")
            if not package.lock.deps:
                lock_tree.add("\\[none]", style="steel_blue1")
            group_renderables = (*group_renderables, padding, lock_tree)

        if modules:
            modules_tree = Tree("Modules", style="steel_blue3")
            for mod in package.modules.values():
                self._add_mod_tree(mod, modules_tree)
            group_renderables = (*group_renderables, padding, modules_tree)

        group = Group(*group_renderables)
        panel = Panel(group, title=info.name, border_style="black")
        self.console.print(panel)


def main(manager: Manager) -> None:
    add_function = Func(
        name="add",
        params={
            "a": Param("a", Type.Int),
            "b": Param("b", Type.Int),
        },
        return_type=Type.Int,
    )

    sub_function = Func(
        name="sub",
        params={
            "a": Param("a", Type.Int),
            "b": Param("b", Type.Int),
        },
        return_type=Type.Int,
    )

    sin_function = Func(
        name="sin",
        params={
            "x": Param("x", Type.Float),
        },
        return_type=Type.Float,
    )

    cos_function = Func(
        name="cos",
        params={
            "x": Param("x", Type.Float),
        },
        return_type=Type.Float,
    )

    tan_function = Func(
        name="tan",
        params={
            "x": Param("x", Type.Float),
        },
        return_type=Type.Float,
    )

    trig_module = Mod(
        name="trig",
        imports=[],
        members={
            "sin": sin_function,
            "cos": cos_function,
            "tan": tan_function,
        },
    )

    math_module = Mod(
        name="math",
        imports=[],
        members={
            "add": add_function,
            "sub": sub_function,
            "trig": trig_module,
        },
    )

    euler_package = Package(
        info=PackageInfo(
            name="euler",
            description="A package for math functions",
            version=Version(major=0, minor=1),
        ),
        modules={"math": math_module},
    )

    main_module = Mod(
        name="main",
        imports=[ImportPath(module_names=["euler", "math"], member_name="add")],
        members={},
    )

    app_package = Package(
        info=PackageInfo(
            name="app",
            description="A fun app",
            version=Version(major=1, minor=2),
        ),
        modules={"main": main_module},
    )

    primary_index = Index(name="primary")
    secondary_index = Index(name="secondary")
    indexes = [primary_index, secondary_index]

    manager.lock(euler_package)
    manager.publish(euler_package, primary_index)

    manager.add(app_package, "euler", indexes)
    manager.lock(app_package)

    manager.print_package_info(euler_package, lock=True, modules=True)
    manager.print_package_info(app_package, lock=True)
