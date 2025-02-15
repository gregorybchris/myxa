import builtins
import logging
from dataclasses import dataclass, field
from typing import Optional

import inflect
from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from myxa.checker import Addition, Change, MemberNodeChange, Removal, VarNodeChange
from myxa.errors import InternalError
from myxa.extra_types import Pluralizer
from myxa.models import (
    Bool,
    Const,
    Dict,
    Enum,
    Field,
    Float,
    Func,
    Index,
    Int,
    List,
    Maybe,
    MemberNode,
    Mod,
    Node,
    Null,
    Package,
    PackageLock,
    Param,
    Set,
    Str,
    Struct,
    Variant,
)

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class Printer:
    console: Console = field(default_factory=Console)
    pluralizer: Pluralizer = field(default_factory=inflect.engine)

    def print_message(self, msg: str) -> None:
        self.console.print(f"[reset][bold]{msg}")

    def print_success(self, msg: str) -> None:
        self.console.print(f"[bold green]{msg}")

    def print_warning(self, msg: str) -> None:
        self.console.print(f"[bold bright_yellow]{msg}")

    def print_error(self, msg: str) -> None:
        self.console.print(f"[bold red]{msg}")

    def input(self, prompt: str) -> str:
        return self.console.input(f"[bold]{prompt}")

    def _add_member_node(self, member_node: MemberNode, tree: Tree) -> None:
        type_builtin = builtins.type
        match member_node:
            case Const(name=name, var_node=var_node):
                var_node_type_str = self.get_node_type_str(var_node)
                tree.add(f"[steel_blue1]{name}[bright_black]: {var_node_type_str}")
            case Struct(name=name, fields=fields):
                struct_tree = tree.add(name, style="steel_blue1")
                for field_name, field_node in fields.items():
                    field_node_type_str = self.get_node_type_str(field_node.var_node)
                    struct_tree.add(f"[red]{field_name}[bright_black]: {field_node_type_str}")
            case Enum(name=name, variants=variants):
                enum_tree = tree.add(name, style="steel_blue1")
                for variant_name, variant_node in variants.items():
                    variant_node_type_str = self.get_node_type_str(variant_node.var_node)
                    variant_node_type = variant_node.var_node.node_type
                    full_var_node_str = (
                        f"[bright_black]({variant_node_type_str}[bright_black])" if variant_node_type != "null" else ""
                    )
                    enum_tree.add(f"[red]{variant_name}{full_var_node_str}")
            case Func(name=name, params=params, return_var_node=return_var_node):
                return_var_node_type_str = self.get_node_type_str(return_var_node)
                func_str = f"[steel_blue1]{name}[bright_black]("
                for param_name, param in params.items():
                    var_node_type_str = self.get_node_type_str(param.var_node)
                    func_str += f"[red]{param_name}[bright_black]: {var_node_type_str}[bright_black], "
                if len(params) > 0:
                    func_str = func_str[:-2]
                func_str += "[bright_black])"
                func_str += f"[bright_black] -> {return_var_node_type_str}"
                tree.add(func_str)
            case Mod(name=name, members=members):
                mod_tree = tree.add(name, style="purple")
                for member in members.values():
                    self._add_member_node(member, mod_tree)
            case _:
                msg = f"Node type not handled: {type_builtin(member_node)}"
                raise InternalError(msg)

    def print_package(  # noqa: PLR0912
        self,
        package: Package,
        show_deps: bool = True,
        show_lock: bool = True,
        show_interface: bool = True,
        index: Optional[Index] = None,
    ) -> None:
        info = package.info

        table = Table(show_header=False, border_style="bright_black")
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
                if index is not None:
                    latest_dep_package = index.get_latest_package(dep.name)
                    is_latest_major = dep.version.major == latest_dep_package.info.version.major
                    version_color = "[green]" if is_latest_major else "[sandy_brown]"
                else:
                    version_color = "[white]"
                deps_tree.add(f"[steel_blue1]{dep.name}[bright_black]~={version_color}{dep.version.to_str()}")
            if not info.deps:
                deps_tree.add("\\[none]", style="steel_blue1")
            group_renderables = (*group_renderables, padding, deps_tree)

        if show_lock and package.lock is not None:
            lock_tree = Tree("Locked dependencies", style="steel_blue3")
            for dep in package.lock.deps.values():
                if index is not None:
                    latest_dep_package = index.get_latest_package(dep.name)
                    is_latest_major = dep.version.major == latest_dep_package.info.version.major
                    version_color = "[green]" if is_latest_major else "[sandy_brown]"
                else:
                    version_color = "[white]"
                lock_tree.add(f"[steel_blue1]{dep.name}[bright_black]=={version_color}{dep.version.to_str()}")
            if not package.lock.deps:
                lock_tree.add("\\[none]", style="steel_blue1")
            group_renderables = (*group_renderables, padding, lock_tree)

        if show_interface:
            mod_tree = Tree("Interface", style="steel_blue3")
            for node in package.members.values():
                self._add_member_node(node, mod_tree)
            if not package.members:
                mod_tree.add("\\[empty]", style="steel_blue1")
            group_renderables = (*group_renderables, padding, mod_tree)

        group = Group(*group_renderables)
        panel = Panel(group, title=info.name, border_style="bright_black")
        self.console.print(panel)

    def print_index(self, index: Index, package_name: Optional[str] = None, show_versions: bool = True) -> None:
        tree = Tree(index.name, style="purple")
        for namespace in index.namespaces.values():
            if package_name is None or package_name == namespace.name:
                namespace_tree = tree.add(namespace.name, style="steel_blue1")
                if show_versions:
                    sorted_packages = sorted(namespace.packages.values(), key=lambda p: p.info.version)
                    for package in sorted_packages:
                        if index is not None:
                            is_latest_major = package.info.version.major == sorted_packages[-1].info.version.major
                            version_color = "[green]" if is_latest_major else "[sandy_brown]"
                        else:
                            version_color = "[white]"
                        namespace_tree.add(
                            f"[steel_blue3]{package.info.name}[bright_black]=={version_color}{package.info.version.to_str()}"
                        )
                    if not namespace.packages:
                        namespace_tree.add("\\[none]", style="steel_blue3")
        if not index.namespaces:
            tree.add("\\[empty]", style="steel_blue1")
        panel = Panel(tree, title=index.name, border_style="bright_black")
        self.console.print(panel)

    def print_lock_diff(self, lock_1: Optional[PackageLock], lock_2: PackageLock) -> None:
        old_deps = set(lock_1.deps.keys()) if lock_1 is not None else set()
        new_deps = set(lock_2.deps.keys())

        additions = new_deps - old_deps
        removals = old_deps - new_deps

        if not additions and not removals:
            self.print_success("Project lock is up to date")
        else:
            self.print_success(
                f"Project lock updated with"
                f" {len(additions)} {self.pluralizer.plural_noun('addition', len(additions))}"
                f" and {len(removals)} {self.pluralizer.plural_noun('removal', len(removals))}"
            )

        for dep_name in additions:
            self.print_message(f"[blue]+ {dep_name}~={lock_2.deps[dep_name].version.to_str()}")
        if lock_1 is not None:
            for dep_name in removals:
                self.print_message(f"[red]- {dep_name}~={lock_1.deps[dep_name].version.to_str()}")

    def print_changes(self, changes: list[Change], comparison_package: Package, breaking_only: bool = False) -> None:
        changes = [change for change in changes if not breaking_only or change.is_breaking()]

        if breaking_only:
            self.print_error(
                f"Found {len(changes)} compatibility {self.pluralizer.plural_noun('break', len(changes))}"
                f" compared to {comparison_package.info.name}=={comparison_package.info.version.to_str()}"
            )
        else:
            self.print_message(
                f"Found {len(changes)} {self.pluralizer.plural_noun('change', len(changes))}"
                f" compared to {comparison_package.info.name}=={comparison_package.info.version.to_str()}"
            )

        for change in changes:
            if not breaking_only or change.is_breaking():
                self.print_change(change)

    def print_change(self, change: Change) -> None:
        match change:
            case Addition(tree_node=tree_node, path=path):
                name = ".".join(path)
                node_str = self.get_node_str(tree_node)
                self.console.print(
                    f"[bright_black]+[steel_blue3] {node_str.title()} [steel_blue1]'{name}'[steel_blue3] has been added"
                )
            case Removal(tree_node=tree_node, path=path):
                name = ".".join(path)
                node_str = self.get_node_str(tree_node)
                self.console.print(
                    f"[bright_black]-[steel_blue3] {node_str.title()}"
                    f" [steel_blue1]'{name}'[steel_blue3] has been removed"
                )
            case VarNodeChange(tree_node=tree_node, old_var_node=old_var_node, new_var_node=new_var_node, path=path):
                node_str = self.get_node_str(tree_node)
                name = ".".join(path)
                old_var_node_type_str = self.get_node_type_str(old_var_node)
                new_var_node_type_str = self.get_node_type_str(new_var_node)
                return_type_str = "return " if isinstance(tree_node, Func) else ""

                self.console.print(
                    f"[bright_black]-[steel_blue3] The {return_type_str}type of"
                    f" {node_str} [steel_blue1]'{name}'[steel_blue3] has changed from"
                    f" {old_var_node_type_str}[steel_blue3]"
                    f" to {new_var_node_type_str}[steel_blue3]"
                )
            case MemberNodeChange(old_member_node=old_member_node, new_member_node=new_member_node, path=path):
                name = ".".join(path)
                old_member_node_type_str = self.get_node_type_str(old_member_node)
                new_member_node_type_str = self.get_node_type_str(new_member_node)
                self.console.print(
                    f"[bright_black]-[steel_blue3] The type of [steel_blue1]'{name}'[steel_blue3] has changed from"
                    f" {old_member_node_type_str}[steel_blue3]"
                    f" to {new_member_node_type_str}[steel_blue3]"
                )
            case _:
                msg = f"Change type {type(change)} is not supported"
                raise InternalError(msg)

    def get_node_str(self, node: Node) -> str:  # noqa: PLR0911, PLR0912
        match node:
            case Bool():
                return "Bool"
            case Const():
                return "Const"
            case Dict():
                return "Dict"
            case Enum():
                return "Enum"
            case Field():
                return "Field"
            case Float():
                return "Float"
            case Func():
                return "Func"
            case Int():
                return "Int"
            case List():
                return "List"
            case Maybe():
                return "Maybe"
            case Mod():
                return "Mod"
            case Null():
                return "Null"
            case Param():
                return "Param"
            case Set():
                return "Set"
            case Str():
                return "Str"
            case Struct():
                return "Struct"
            case Variant():
                return "Variant"
            case _:
                msg = f"Node type {type(node)} is not supported"
                raise InternalError(msg)

    def get_node_type_str(self, node: Node) -> str:  # noqa: PLR0911, PLR0912
        g = "[light_goldenrod2]"
        s = "[sandy_brown]"
        b = "[bright_black]"
        match node:
            case Struct(name=name, fields=fields):
                field_node_type_strs = [self.get_node_type_str(field) for field in fields.values()]
                fields_str = f"{b}, ".join(field_node_type_strs)
                return f"{g}Struct{b}({s}{name}{b})[{fields_str}{b}]"
            case Field(name=name, var_node=var_node):
                var_node_type_str = self.get_node_type_str(var_node)
                return f"{s}{name}{b}({s}{var_node_type_str}{b})"
            case Enum(name=name, variants=variants):
                variant_node_type_strs = [self.get_node_type_str(variant) for variant in variants.values()]
                variants_str = f"{b}, ".join(variant_node_type_strs)
                return f"{g}Enum{b}({s}{name}{b})[{variants_str}{b}]"
            case Variant(name=name, var_node=var_node):
                var_node_type_str = self.get_node_type_str(var_node)
                if var_node.node_type == "null":
                    return f"{s}{name}"
                return f"{s}{name}{b}({s}{var_node_type_str}{b})"
            case Func(params=params, return_var_node=return_var_node):
                param_node_type_strs = [self.get_node_type_str(param.var_node) for _, param in params.items()]
                params_str = f"{b}, ".join(param_node_type_strs)
                return_var_node_type_str = self.get_node_type_str(return_var_node)
                return f"{g}Func{b}[[{g}{params_str}{b}], {g}{return_var_node_type_str}{b}]"
            case Param(var_node=var_node):
                var_node_type_str = self.get_node_type_str(var_node)
                return f"{g}Param{b}[{g}{var_node_type_str}{b}]"
            case Maybe(var_node=var_node):
                var_node_type_str = self.get_node_type_str(var_node)
                return f"{g}Maybe{b}[{g}{var_node_type_str}{b}]"
            case List(var_node=var_node):
                var_node_type_str = self.get_node_type_str(var_node)
                return f"{g}List{b}[{g}{var_node_type_str}{b}]"
            case Set(var_node=var_node):
                var_node_type_str = self.get_node_type_str(var_node)
                return f"{g}Set{b}[{g}{var_node_type_str}{b}]"
            case Dict(key_var_node=key_var_node, val_var_node=val_var_node):
                key_var_node_type_str = self.get_node_type_str(key_var_node)
                val_var_node_type_str = self.get_node_type_str(val_var_node)
                return f"{g}Dict{b}[{g}{key_var_node_type_str}{b}, {g}{val_var_node_type_str}{b}]"
            case Const(var_node=var_node):
                var_node_type_str = self.get_node_type_str(var_node)
                return f"{g}Const{b}[{g}{var_node_type_str}{b}]"
            case _:
                return f"{g}{self.get_node_str(node)}"
