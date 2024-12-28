import builtins
import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, Optional, Self, Union

import inflect
from pydantic import BaseModel, Field
from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

logger = logging.getLogger(__name__)


class Type(StrEnum):
    Bool = "Bool"
    Float = "Float"
    Int = "Int"
    Null = "Null"
    Str = "Str"


class Const(BaseModel):
    node_type: Literal["const"] = "const"
    name: str
    type: Type


class Param(BaseModel):
    name: str
    type: Type


class Func(BaseModel):
    node_type: Literal["func"] = "func"
    name: str
    params: dict[str, Param]
    return_type: Type


class Import(BaseModel):
    path: list[str]
    member_names: list[str]


class Mod(BaseModel):
    node_type: Literal["mod"] = "mod"
    name: str
    imports: list[Import]
    members: dict[str, "Node"]


Node = Union[Const, Func, Mod]


class Version(BaseModel):
    major: int
    minor: int

    def to_str(self) -> str:
        return f"{self.major}.{self.minor}"

    @classmethod
    def from_str(cls, s: str) -> Self:
        parts = s.split(".")
        major = int(parts[0])
        minor = int(parts[1])
        return cls(major=major, minor=minor)

    def __hash__(self) -> int:
        return hash(str(self))


class Dep(BaseModel):
    name: str
    version: Version


class PackageLock(BaseModel):
    deps: dict[str, Dep] = Field(default_factory=dict)


class PackageInfo(BaseModel):
    name: str
    description: str
    version: Version
    deps: dict[str, Dep] = Field(default_factory=dict)


class Package(BaseModel):
    info: PackageInfo
    lock: Optional[PackageLock] = None
    members: dict[str, Node]


class Namespace(BaseModel):
    name: str
    packages: dict[str, Package] = Field(default_factory=dict)


class Index(BaseModel):
    name: str
    namespaces: dict[str, Namespace] = Field(default_factory=dict)


class InternalError(Exception):
    pass


class UserError(Exception):
    pass


@dataclass(kw_only=True)
class Printer:
    console: Console

    def print_error(self, msg: str) -> None:
        self.console.print(f"[bold red]{msg}")

    def print_message(self, msg: str) -> None:
        self.console.print(f"[reset][bold]{msg}")

    def print_success(self, msg: str) -> None:
        self.console.print(f"[bold green]{msg}")

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

    def print_package(
        self,
        package: Package,
        show_deps: bool = False,
        show_lock: bool = False,
        show_modules: bool = False,
    ) -> None:
        info = package.info

        table = Table(show_header=False, border_style="black")
        table.add_column("", style="steel_blue3")
        table.add_column("", style="steel_blue1")
        table.add_row("Name", info.name)
        table.add_row("Description", info.description)
        table.add_row("Version", info.version.to_str())

        padding = Padding("")

        group_renderables: tuple = (table,)
        if show_deps:
            deps_tree = Tree("Dependencies", style="steel_blue3")
            for dep in info.deps.values():
                deps_tree.add(f"{dep.name}~={dep.version.to_str()}", style="steel_blue1")
            if not info.deps:
                deps_tree.add("\\[none]", style="steel_blue1")
            group_renderables = (*group_renderables, padding, deps_tree)

        if show_lock:
            if package.lock is None:
                msg = f"No lock found for package {package.info.name}"
                raise UserError(msg)

            lock_tree = Tree("Locked dependencies", style="steel_blue3")
            for dep in package.lock.deps.values():
                lock_tree.add(f"{dep.name}=={dep.version.to_str()}", style="steel_blue1")
            if not package.lock.deps:
                lock_tree.add("\\[none]", style="steel_blue1")
            group_renderables = (*group_renderables, padding, lock_tree)

        if show_modules:
            modules_tree = Tree("Interface", style="steel_blue3")
            for node in package.members.values():
                self._add_tree_node(node, modules_tree)
            group_renderables = (*group_renderables, padding, modules_tree)

        group = Group(*group_renderables)
        panel = Panel(group, title=info.name, border_style="black")
        self.console.print(panel)

    def print_index(self, index: Index, show_versions: bool = False) -> None:
        tree = Tree(index.name, style="purple")
        for namespace in index.namespaces.values():
            namespace_tree = tree.add(namespace.name, style="steel_blue1")
            if show_versions:
                for package in namespace.packages.values():
                    namespace_tree.add(f"{package.info.name}=={package.info.version.to_str()}", style="steel_blue3")
        if not index.namespaces:
            tree.add("\\[empty]", style="steel_blue1")
        panel = Panel(tree, title=index.name, border_style="black")
        self.console.print(panel)


@dataclass(kw_only=True)
class Manager:
    printer: Printer
    inflect_engine: inflect.engine

    def init(self, name: str, description: str) -> Package:
        self.printer.print_message(f"Initializing package {name}...")
        package = Package(
            info=PackageInfo(name=name, description=description, version=Version(major=0, minor=1)),
            members={},
        )
        self.printer.print_success(f"Initialized {name}")
        return package

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
        dep = Dep(name=dep_name, version=version)
        package.info.deps[dep_name] = dep
        self.printer.print_success(f"Added {dep_name} version {version} to {package.info.name}")

    def remove(self, package: Package, dep_name: str) -> None:
        self.printer.print_message(f"Removing dependency {dep_name} from package {package.info.name}...")
        if dep := package.info.deps.pop(dep_name, None):
            self.printer.print_success(f"Removed {dep_name} version {dep.version} from {package.info.name}")
        else:
            self.printer.print_success(f"{dep_name} is not a dependency of {package.info.name}")

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
            msg = f"Package file not found: {package_filepath}"
            raise UserError(msg)
        with package_filepath.open("r") as fp:
            package_dict = json.load(fp)
        return Package(**package_dict)

    def save_package(self, package: Package, package_filepath: Path) -> None:
        with package_filepath.open("w") as fp:
            fp.write(package.model_dump_json(indent=2))

    def load_index(self, index_filepath: Path) -> Index:
        if not index_filepath.exists():
            msg = f"Index file not found: {index_filepath}"
            raise UserError(msg)
        with index_filepath.open("r") as fp:
            index_dict = json.load(fp)
        return Index(**index_dict)

    def save_index(self, index: Index, index_filepath: Path) -> None:
        with index_filepath.open("w") as fp:
            fp.write(index.model_dump_json(indent=2))
