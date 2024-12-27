import builtins
import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, Optional, Union

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

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"

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
    packages: dict[Version, Package] = Field(default_factory=dict)


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


@dataclass(kw_only=True)
class Manager:
    printer: Printer
    inflect_engine: inflect.engine

    def publish(self, package: Package, index: Index) -> None:
        self.printer.print_message(
            f"Publishing package {package.info.name} version {package.info.version} to index {index.name}..."
        )
        if package.lock is None:
            msg = f"No lock found for package {package.info.name}, unable to publish it to index {index.name}"
            raise UserError(msg)

        # TODO: Check package name is valid with regex
        # TODO: Check that the version is incremented only by one (minor or major), should not skip a major or minor
        # TODO: Check that the info hasn't been updated more recently than the lock

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
        self.printer.print_success(f"Published {info.name} version {info.version} to index {index.name}")

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
        self.printer.print_message(f"Adding dependency {dep_name} to package {package.info.name}...")
        if package.info.deps.get(dep_name):
            msg = f"{dep_name} is already a dependency of {package.info.name}"
            raise UserError(msg)

        # TODO: Resolve the latest compatible version of the dep
        namespace = self._find_namespace(dep_name, indexes)
        latest_package = self._get_latest_package(namespace)
        version = latest_package.info.version
        dep = Dep(name=dep_name, version=version)
        package.info.deps[dep_name] = dep
        self.printer.print_success(f"Added {dep_name} version {version} to {package.info.name}")

    def _resolve(self, package: Package, indexes: list[Index]) -> None:
        pass

    def lock(self, package: Package) -> None:
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
        with package_filepath.open("r") as fp:
            package_dict = json.load(fp)
        return Package(**package_dict)

    def save_package(self, package: Package, package_filepath: Path) -> None:
        with package_filepath.open("w") as fp:
            json.dump(package.model_dump(), fp, indent=2)


def main(manager: Manager, printer: Printer) -> None:
    examples_dirpath = Path(__file__).parent.parent.parent / "examples"
    euler_package_filepath = examples_dirpath / "euler.json"
    flatty_package_filepath = examples_dirpath / "flatty.json"
    interlet_package_filepath = examples_dirpath / "interlet.json"
    app_package_filepath = examples_dirpath / "app.json"

    euler_package = manager.load_package(euler_package_filepath)
    flatty_package = manager.load_package(flatty_package_filepath)
    interlet_package = manager.load_package(interlet_package_filepath)
    app_package = manager.load_package(app_package_filepath)

    primary_index = Index(name="primary")
    secondary_index = Index(name="secondary")
    indexes = [primary_index, secondary_index]

    manager.lock(euler_package)
    manager.publish(euler_package, primary_index)

    manager.lock(flatty_package)
    manager.publish(flatty_package, primary_index)

    # manager.add(interlet_package, flatty_package.info.name, indexes)
    manager.lock(interlet_package)
    manager.publish(interlet_package, primary_index)

    # manager.add(app_package, euler_package.info.name, indexes)
    # manager.add(app_package, interlet_package.info.name, indexes)
    manager.lock(app_package)

    printer.print_package_info(euler_package, lock=True, modules=True)
    printer.print_package_info(flatty_package, lock=True, modules=True)
    printer.print_package_info(interlet_package, lock=True, modules=True)
    printer.print_package_info(app_package, lock=True, modules=True)

    manager.save_package(euler_package, euler_package_filepath)
    manager.save_package(flatty_package, flatty_package_filepath)
    manager.save_package(interlet_package, interlet_package_filepath)
    manager.save_package(app_package, app_package_filepath)
