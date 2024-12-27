import builtins
import logging
import sys
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
    Null = "Null"


@dataclass(kw_only=True)
class Node:
    pass


@dataclass(kw_only=True)
class Const(Node):
    name: str
    type: Type


@dataclass(kw_only=True)
class Param:
    name: str
    type: Type


@dataclass(kw_only=True)
class Func(Node):
    name: str
    params: dict[str, Param]
    return_type: Type


@dataclass(kw_only=True)
class Import:
    path: list[str]
    member_names: list[str]


@dataclass(kw_only=True)
class Mod(Node):
    name: str
    imports: list[Import]
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
    members: dict[str, Node]


@dataclass(kw_only=True)
class Namespace:
    name: str
    packages: dict[Version, Package] = field(default_factory=dict)


@dataclass(kw_only=True)
class Index:
    name: str
    namespaces: dict[str, Namespace] = field(default_factory=dict)


class InternalError(Exception):
    pass


class UserError(Exception):
    pass


@dataclass(kw_only=True)
class Manager:
    console: Console

    def error(self, msg: str) -> None:
        self.console.print(f"[bold red]{msg}")
        sys.exit()

    def publish(self, package: Package, index: Index) -> None:
        if package.lock is None:
            msg = f"No lock found for package {package.info.name}, unable to publish it to index {index.name}"
            raise UserError(msg)

        # TODO: Check package name is valid with regex
        # TODO: Check that the version is incremented only by one (minor or major)

        info = package.info
        if namespace := index.namespaces.get(info.name):
            # TODO: Check that if this package correctly increments major version if changes are breaking
            if info.version in namespace.packages:
                msg = f"Package {info.name} version {info.version} already exists in index {index.name}"
                raise UserError(msg)
            namespace.packages[info.version] = package
        else:
            namespace = Namespace(name=info.name)
            namespace.packages[info.version] = package
            index.namespaces[info.name] = namespace

    def _find_namespace(self, name: str, indexes: list[Index]) -> Namespace:
        for index in indexes:
            if namespace := index.namespaces.get(name):
                return namespace
        msg = f"Package {name} not found in any provided indexes: {[index.name for index in indexes]}"
        raise UserError(msg)

    def _get_latest_package(self, namespace: Namespace) -> Package:
        versions = list(namespace.packages.keys())
        latest_version = max(versions, key=lambda v: (v.major, v.minor))
        return namespace.packages[latest_version]

    def add(self, package: Package, dep_name: str, indexes: list[Index]) -> None:
        self.console.print(f"Adding [steel_blue1]{dep_name}[reset] to [steel_blue1]{package.info.name}[reset]...")
        if package.info.deps.get(dep_name):
            msg = f"{dep_name} is already a dependency of {package.info.name}"
            raise UserError(msg)

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

    def _add_tree_node(self, node: Node, tree: Tree) -> None:
        type_builtin = builtins.type
        match node:
            case Const(name=name, type=type):
                tree.add(f"[steel_blue1]{name}[black]: [sandy_brown]{type}")
            case Func(name=name, params=params, return_type=return_type):
                func_str = f"[steel_blue1]{name}[black]("
                for param_name, param in params.items():
                    func_str += f"[red]{param_name}[black]: [light_goldenrod2]{param.type}, "
                if len(params) > 0:
                    func_str = func_str[:-2]
                func_str += "[black])"
                func_str += f"[black] -> [sandy_brown]{return_type}"
                tree.add(func_str)
            case Mod(name=name, members=members):
                mod_tree = tree.add(name, style="purple")
                for member in members.values():
                    self._add_tree_node(member, mod_tree)
            case _:
                msg = f"Node type not handled: {type_builtin(node)}"
                raise InternalError(msg)

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
                raise UserError(msg)

            lock_tree = Tree("Locked dependencies", style="steel_blue3")
            for dep in package.lock.deps.values():
                lock_tree.add(f"{dep.name}=={dep.version}", style="steel_blue1")
            if not package.lock.deps:
                lock_tree.add("\\[none]", style="steel_blue1")
            group_renderables = (*group_renderables, padding, lock_tree)

        if modules:
            modules_tree = Tree("Interface", style="steel_blue3")
            for node in package.members.values():
                self._add_tree_node(node, modules_tree)
            group_renderables = (*group_renderables, padding, modules_tree)

        group = Group(*group_renderables)
        panel = Panel(group, title=info.name, border_style="black")
        self.console.print(panel)


def main(manager: Manager) -> None:
    try:
        add_function = Func(
            name="add",
            params={
                "a": Param(name="a", type=Type.Int),
                "b": Param(name="b", type=Type.Int),
            },
            return_type=Type.Int,
        )

        sub_function = Func(
            name="sub",
            params={
                "a": Param(name="a", type=Type.Int),
                "b": Param(name="b", type=Type.Int),
            },
            return_type=Type.Int,
        )

        sin_function = Func(
            name="sin",
            params={
                "x": Param(name="x", type=Type.Float),
            },
            return_type=Type.Float,
        )

        cos_function = Func(
            name="cos",
            params={
                "x": Param(name="x", type=Type.Float),
            },
            return_type=Type.Float,
        )

        tan_function = Func(
            name="tan",
            params={
                "x": Param(name="x", type=Type.Float),
            },
            return_type=Type.Float,
        )

        pi_const = Const(name="pi", type=Type.Float)
        e_const = Const(name="e", type=Type.Float)

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
                "pi": pi_const,
                "e": e_const,
                "add": add_function,
                "sub": sub_function,
                "trig": trig_module,
            },
        )

        euler_package = Package(
            info=PackageInfo(
                name="euler",
                description="A compilation of useful math stuff",
                version=Version(major=0, minor=1),
            ),
            members={"math": math_module},
        )

        serialize_function = Func(
            name="serialize",
            params={
                "data": Param(name="s", type=Type.Str),
            },
            return_type=Type.Str,
        )

        deserialize_function = Func(
            name="deserialize",
            params={
                "data": Param(name="s", type=Type.Str),
            },
            return_type=Type.Str,
        )

        flatty_package = Package(
            info=PackageInfo(
                name="flatty",
                description="A package for serializing and deserializing data",
                version=Version(major=2, minor=0),
            ),
            members={
                "serialize": serialize_function,
                "deserialize": deserialize_function,
            },
        )

        serve_function = Func(
            name="serve",
            params={
                "host": Param(name="host", type=Type.Str),
                "port": Param(name="port", type=Type.Int),
            },
            return_type=Type.Null,
        )

        router_module = Mod(
            name="router",
            imports=[Import(path=["flatty"], member_names=["serialize", "deserialize"])],
            members={"serve": serve_function},
        )

        interlet_package = Package(
            info=PackageInfo(
                name="interlet",
                description="A blazingly fast webserver",
                version=Version(major=3, minor=4),
            ),
            members={"router": router_module},
        )

        run_function = Func(
            name="run",
            params={},
            return_type=Type.Null,
        )

        main_module = Mod(
            name="main",
            imports=[
                Import(path=["euler", "math"], member_names=["add"]),
                Import(path=["interlet", "router"], member_names=["serve"]),
            ],
            members={"run": run_function},
        )

        app_package = Package(
            info=PackageInfo(
                name="app",
                description="A fun app for doing math",
                version=Version(major=1, minor=2),
            ),
            members={"main": main_module},
        )

        primary_index = Index(name="primary")
        secondary_index = Index(name="secondary")
        indexes = [primary_index, secondary_index]

        manager.lock(euler_package)
        manager.publish(euler_package, primary_index)

        manager.lock(flatty_package)
        manager.publish(flatty_package, primary_index)

        manager.add(interlet_package, "flatty", indexes)
        manager.lock(interlet_package)
        manager.publish(interlet_package, primary_index)

        manager.add(app_package, "euler", indexes)
        manager.add(app_package, "interlet", indexes)
        manager.lock(app_package)

        manager.print_package_info(euler_package, lock=True, modules=True)
        manager.print_package_info(flatty_package, lock=True, modules=True)
        manager.print_package_info(interlet_package, lock=True, modules=True)
        manager.print_package_info(app_package, lock=True, modules=True)
    except UserError as exc:
        manager.error(str(exc))
