import logging
from dataclasses import dataclass
from typing import Iterator

from pydantic import BaseModel

from myxa.errors import InternalError
from myxa.models import Const, Func, Mod, Package, Param, TreeNode, VarNode

logger = logging.getLogger(__name__)

Path = list[str]


class CompatBreak(BaseModel):
    pass


class Removal(CompatBreak):
    tree_node: TreeNode
    path: Path


class TypeChange(CompatBreak):
    tree_node: TreeNode
    old_var_node: VarNode
    new_var_node: VarNode
    path: Path


class NodeChange(CompatBreak):
    old_tree_node: TreeNode
    new_tree_node: TreeNode
    path: Path


@dataclass
class Checker:
    def check(self, package_old: Package, package_new: Package) -> list[CompatBreak]:
        return list(self._check(package_old, package_new))

    def _check(self, package_old: Package, package_new: Package) -> Iterator[CompatBreak]:
        package_name = package_old.info.name
        for member_name, member_old in package_old.members.items():
            if member_new := package_new.members.get(member_name):
                yield from self._check_tree_node(member_old, member_new, [package_name, member_name])
            else:
                yield from self._handle_tree_node_removed(member_old, [package_name, member_name])

    def _check_tree_node(self, tree_node_old: TreeNode, tree_node_nw: TreeNode, path: Path) -> Iterator[CompatBreak]:
        for node in (tree_node_old, tree_node_nw):
            if not isinstance(node, (Mod, Func, Const)):
                msg = f"Invalid node type {type(node)}, not permitted"
                raise InternalError(msg)

        match tree_node_old, tree_node_nw:
            case (Mod() as mod_old, Mod() as mod_new):
                yield from self._check_mod(mod_old, mod_new, path)
            case (Func() as func_old, Func() as func_new):
                yield from self._check_func(func_old, func_new, path)
            case (Const() as const_old, Const() as const_new):
                yield from self._check_const(const_old, const_new, path)
            case _:
                yield NodeChange(old_tree_node=tree_node_old, new_tree_node=tree_node_nw, path=path)

    def _check_mod(self, mod_old: Mod, mod_new: Mod, path: Path) -> Iterator[CompatBreak]:
        for member_name, member_old in mod_old.members.items():
            if member_new := mod_new.members.get(member_name):
                yield from self._check_tree_node(member_old, member_new, [*path, member_name])
            else:
                yield from self._handle_tree_node_removed(member_old, [*path, member_name])

    def _check_func(self, func_old: Func, func_new: Func, path: Path) -> Iterator[CompatBreak]:
        if func_old.return_var_node != func_new.return_var_node:
            yield TypeChange(
                tree_node=func_old,
                old_var_node=func_old.return_var_node,
                new_var_node=func_new.return_var_node,
                path=path,
            )

        for param_name, param_old in func_old.params.items():
            if param_new := func_new.params.get(param_name):
                yield from self._check_param(param_old, param_new, [*path, param_name])
            else:
                yield from self._handle_tree_node_removed(param_old, [*path, param_name])

    def _check_param(self, param_old: Param, param_new: Param, path: Path) -> Iterator[CompatBreak]:
        if param_old.var_node != param_new.var_node:
            yield TypeChange(
                tree_node=param_old, old_var_node=param_old.var_node, new_var_node=param_new.var_node, path=path
            )

    def _check_const(self, const_old: Const, const_new: Const, path: Path) -> Iterator[CompatBreak]:
        if const_old.var_node != const_new.var_node:
            yield TypeChange(
                tree_node=const_old, old_var_node=const_old.var_node, new_var_node=const_new.var_node, path=path
            )

    def _handle_tree_node_removed(self, tree_node_old: TreeNode, path: Path) -> Iterator[CompatBreak]:
        match tree_node_old:
            case Mod():
                yield Removal(tree_node=tree_node_old, path=path)
            case Func():
                yield Removal(tree_node=tree_node_old, path=path)
            case Param():
                yield Removal(tree_node=tree_node_old, path=path)
            case Const():
                yield Removal(tree_node=tree_node_old, path=path)
            case _:
                msg = f"Checking for {type(tree_node_old)} nodes is not implemented"
                raise NotImplementedError(msg)
