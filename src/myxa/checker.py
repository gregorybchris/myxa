import logging
from dataclasses import dataclass
from typing import Iterator

from pydantic import BaseModel

from myxa.errors import InternalError
from myxa.models import Const, Field, Func, Mod, Package, Param, Struct, TreeNode, VarNode

logger = logging.getLogger(__name__)

Path = list[str]
Members = dict[str, TreeNode]


class Change(BaseModel):
    def is_breaking(self) -> bool:
        return isinstance(self, (Removal, VarNodeChange, TreeNodeChange))


class Addition(Change):
    tree_node: TreeNode
    path: Path


class Removal(Change):
    tree_node: TreeNode
    path: Path


class VarNodeChange(Change):
    tree_node: TreeNode
    old_var_node: VarNode
    new_var_node: VarNode
    path: Path


class TreeNodeChange(Change):
    old_tree_node: TreeNode
    new_tree_node: TreeNode
    path: Path


@dataclass
class Checker:
    def diff(self, package_old: Package, package_new: Package) -> list[Change]:
        return list(self._diff(package_old, package_new))

    def _diff(self, package_old: Package, package_new: Package) -> Iterator[Change]:
        package_name = package_old.info.name
        package_path = [package_name]
        yield from self._diff_members(package_old.members, package_new.members, package_path)

    def _diff_members(self, members_old: Members, members_new: Members, path: Path) -> Iterator[Change]:
        old_member_names = set(members_old.keys())
        new_member_names = set(members_new.keys())
        all_member_names = sorted(old_member_names.union(new_member_names))
        for member_name in all_member_names:
            member_path = [*path, member_name]
            if member_name in old_member_names and member_name in new_member_names:
                yield from self._diff_tree_node(members_old[member_name], members_new[member_name], member_path)
            elif member_name in old_member_names:
                yield from self._handle_tree_node_removal(members_old[member_name], member_path)
            else:
                yield from self._handle_tree_node_addition(members_new[member_name], member_path)

    def _diff_tree_node(self, tree_node_old: TreeNode, tree_node_new: TreeNode, path: Path) -> Iterator[Change]:
        for node in (tree_node_old, tree_node_new):
            if not isinstance(node, (Mod, Struct, Func, Const)):
                msg = f"Invalid node type {type(node)}, not permitted"
                raise InternalError(msg)

        match tree_node_old, tree_node_new:
            case (Mod() as mod_old, Mod() as mod_new):
                yield from self._diff_mod(mod_old, mod_new, path)
            case (Struct() as struct_old, Struct() as struct_new):
                yield from self._diff_struct(struct_old, struct_new, path)
            case (Func() as func_old, Func() as func_new):
                yield from self._diff_func(func_old, func_new, path)
            case (Const() as const_old, Const() as const_new):
                yield from self._diff_const(const_old, const_new, path)
            case _:
                yield TreeNodeChange(old_tree_node=tree_node_old, new_tree_node=tree_node_new, path=path)

    def _diff_mod(self, mod_old: Mod, mod_new: Mod, path: Path) -> Iterator[Change]:
        yield from self._diff_members(mod_old.members, mod_new.members, path)

    def _diff_struct(self, struct_old: Struct, struct_new: Struct, path: Path) -> Iterator[Change]:
        old_field_names = set(struct_old.fields.keys())
        new_field_names = set(struct_new.fields.keys())
        all_field_names = sorted(old_field_names.union(new_field_names))
        for field_name in all_field_names:
            field_path = [*path, field_name]
            if field_name in old_field_names and field_name in new_field_names:
                yield from self._diff_field(struct_old.fields[field_name], struct_new.fields[field_name], field_path)
            elif field_name in old_field_names:
                yield from self._handle_tree_node_removal(struct_old.fields[field_name], field_path)
            else:
                yield from self._handle_tree_node_addition(struct_new.fields[field_name], field_path)

    def _diff_field(self, field_old: Field, field_new: Field, path: Path) -> Iterator[Change]:
        if field_old.var_node != field_new.var_node:
            yield VarNodeChange(
                tree_node=field_old, old_var_node=field_old.var_node, new_var_node=field_new.var_node, path=path
            )

    def _diff_func(self, func_old: Func, func_new: Func, path: Path) -> Iterator[Change]:
        if func_old.return_var_node != func_new.return_var_node:
            yield VarNodeChange(
                tree_node=func_old,
                old_var_node=func_old.return_var_node,
                new_var_node=func_new.return_var_node,
                path=path,
            )

        old_param_names = set(func_old.params.keys())
        new_param_names = set(func_new.params.keys())
        all_param_names = sorted(old_param_names.union(new_param_names))
        for param_name in all_param_names:
            param_path = [*path, param_name]
            if param_name in old_param_names and param_name in new_param_names:
                yield from self._diff_param(func_old.params[param_name], func_new.params[param_name], param_path)
            elif param_name in old_param_names:
                yield from self._handle_tree_node_removal(func_old.params[param_name], param_path)
            else:
                yield from self._handle_tree_node_addition(func_new.params[param_name], param_path)

    def _diff_param(self, param_old: Param, param_new: Param, path: Path) -> Iterator[Change]:
        if param_old.var_node != param_new.var_node:
            yield VarNodeChange(
                tree_node=param_old, old_var_node=param_old.var_node, new_var_node=param_new.var_node, path=path
            )

    def _diff_const(self, const_old: Const, const_new: Const, path: Path) -> Iterator[Change]:
        if const_old.var_node != const_new.var_node:
            yield VarNodeChange(
                tree_node=const_old, old_var_node=const_old.var_node, new_var_node=const_new.var_node, path=path
            )

    def _handle_tree_node_removal(self, tree_node: TreeNode, path: Path) -> Iterator[Change]:
        yield Removal(tree_node=tree_node, path=path)

    def _handle_tree_node_addition(self, tree_node: TreeNode, path: Path) -> Iterator[Change]:
        yield Addition(tree_node=tree_node, path=path)
