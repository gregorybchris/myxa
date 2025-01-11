import logging
from dataclasses import dataclass
from typing import Iterator, get_args

from pydantic import BaseModel

from myxa.errors import InternalError
from myxa.models import (
    Const,
    Enum,
    Field,
    Func,
    MemberNode,
    Mod,
    Package,
    Param,
    Struct,
    TreeNode,
    Variant,
    VarNode,
)

logger = logging.getLogger(__name__)

Path = list[str]
Members = dict[str, MemberNode]


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
                yield from self._diff_member_node(members_old[member_name], members_new[member_name], member_path)
            elif member_name in old_member_names:
                yield from self._handle_tree_node_removal(members_old[member_name], member_path)
            else:
                yield from self._handle_tree_node_addition(members_new[member_name], member_path)

    def _diff_member_node(
        self,
        member_node_old: MemberNode,
        member_node_new: MemberNode,
        path: Path,
    ) -> Iterator[Change]:
        for node in (member_node_old, member_node_new):
            if not isinstance(node, get_args(MemberNode)):
                msg = f"Invalid MemberNode type {type(node)}"
                raise InternalError(msg)

        match member_node_old, member_node_new:
            case (Mod() as mod_old, Mod() as mod_new):
                yield from self._diff_mod(mod_old, mod_new, path)
            case (Struct() as struct_old, Struct() as struct_new):
                yield from self._diff_struct(struct_old, struct_new, path)
            case (Enum() as enum_old, Enum() as enum_new):
                yield from self._diff_enum(enum_old, enum_new, path)
            case (Func() as func_old, Func() as func_new):
                yield from self._diff_func(func_old, func_new, path)
            case (Const() as const_old, Const() as const_new):
                yield from self._diff_const(const_old, const_new, path)
            case _:
                yield TreeNodeChange(old_tree_node=member_node_old, new_tree_node=member_node_new, path=path)

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
        yield from self._diff_var_node(field_old, field_old.var_node, field_new.var_node, path)

    def _diff_enum(self, enum_old: Enum, enum_new: Enum, path: Path) -> Iterator[Change]:
        old_variant_names = set(enum_old.variants.keys())
        new_variant_names = set(enum_new.variants.keys())
        all_variant_names = sorted(old_variant_names.union(new_variant_names))
        for variant_name in all_variant_names:
            variant_path = [*path, variant_name]
            if variant_name in old_variant_names and variant_name in new_variant_names:
                yield from self._diff_variant(
                    enum_old.variants[variant_name], enum_new.variants[variant_name], variant_path
                )
            elif variant_name in old_variant_names:
                yield from self._handle_tree_node_removal(enum_old.variants[variant_name], variant_path)
            else:
                yield from self._handle_tree_node_addition(enum_new.variants[variant_name], variant_path)

    def _diff_variant(self, variant_old: Variant, variant_new: Variant, path: Path) -> Iterator[Change]:
        yield from self._diff_var_node(variant_old, variant_old.var_node, variant_new.var_node, path)

    def _diff_func(self, func_old: Func, func_new: Func, path: Path) -> Iterator[Change]:
        yield from self._diff_var_node(func_old, func_old.return_var_node, func_new.return_var_node, path)

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
        yield from self._diff_var_node(param_old, param_old.var_node, param_new.var_node, path)

    def _diff_const(self, const_old: Const, const_new: Const, path: Path) -> Iterator[Change]:
        yield from self._diff_var_node(const_old, const_old.var_node, const_new.var_node, path)

    def _handle_tree_node_removal(self, tree_node: TreeNode, path: Path) -> Iterator[Change]:
        yield Removal(tree_node=tree_node, path=path)

    def _handle_tree_node_addition(self, tree_node: TreeNode, path: Path) -> Iterator[Change]:
        yield Addition(tree_node=tree_node, path=path)

    def _diff_var_node(
        self,
        tree_node: TreeNode,
        var_node_old: VarNode,
        var_node_new: VarNode,
        path: Path,
    ) -> Iterator[Change]:
        for node in (var_node_old, var_node_new):
            if not isinstance(node, get_args(VarNode)):
                msg = f"Invalid VarNode type {type(node)}"
                raise InternalError(msg)

        match var_node_old, var_node_new:
            case (Struct() as struct_old, Struct() as struct_new):
                yield from self._diff_struct(struct_old, struct_new, [*path, struct_old.name])
            case (Enum() as enum_old, Enum() as enum_new):
                yield from self._diff_enum(enum_old, enum_new, [*path, enum_old.name])
            case (Func() as func_old, Func() as func_new):
                yield from self._diff_func(func_old, func_new, [*path, func_old.name])
            case _:
                if var_node_old.node_type != var_node_new.node_type:
                    yield VarNodeChange(
                        tree_node=tree_node,
                        old_var_node=var_node_old,
                        new_var_node=var_node_new,
                        path=path,
                    )
                else:
                    for node in (var_node_old, var_node_new):
                        if isinstance(node, get_args(TreeNode)):
                            # If the types are different we can stop recursing, but if they are the same
                            # we need to check whether they are TreeNode types
                            # TreeNode types must be handled explicitly because they can contain VarNodes
                            # that might have changed.
                            msg = f"VarNodes that are TreeNodes must be handled explicitly: {type(node)}"
                            raise InternalError(msg)
