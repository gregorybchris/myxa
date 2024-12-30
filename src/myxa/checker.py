import logging
from dataclasses import dataclass
from typing import Iterator

from pydantic import BaseModel

from myxa.errors import InternalError
from myxa.models import Const, Func, Mod, Node, Package, Param, Type

logger = logging.getLogger(__name__)

Path = list[str]


class CompatBreak(BaseModel):
    pass


class Removal(CompatBreak):
    node: Node
    path: Path


class TypeChange(CompatBreak):
    node: Node
    old_type: Type
    new_type: Type
    path: Path


class NodeTypeChange(CompatBreak):
    old_node: Node
    new_node: Node
    path: Path


@dataclass
class Checker:
    def check(self, package_old: Package, package_new: Package) -> list[CompatBreak]:
        package_name = package_old.info.name
        breaks: list[CompatBreak] = []
        for member_name, member_old in package_old.members.items():
            if member_new := package_new.members.get(member_name):
                breaks.extend(self._check_node(member_old, member_new, [package_name, member_name]))
            else:
                breaks.extend(self._handle_node_removed(member_old, [package_name, member_name]))
        return breaks

    def _check_node(self, node_old: Node, node_new: Node, path: Path) -> Iterator[CompatBreak]:
        for node in (node_old, node_new):
            if not isinstance(node, (Mod, Func, Const)):
                msg = f"Invalid node type {type(node)}, not permitted"
                raise InternalError(msg)

        match node_old, node_new:
            case (Mod() as mod_old, Mod() as mod_new):
                yield from self._check_mod(mod_old, mod_new, path)
            case (Func() as func_old, Func() as func_new):
                yield from self._check_func(func_old, func_new, path)
            case (Const() as const_old, Const() as const_new):
                yield from self._check_const(const_old, const_new, path)
            case _:
                yield NodeTypeChange(old_node=node_old, new_node=node_new, path=path)

    def _check_mod(self, mod_old: Mod, mod_new: Mod, path: Path) -> Iterator[CompatBreak]:
        for member_name, member_old in mod_old.members.items():
            if member_new := mod_new.members.get(member_name):
                yield from self._check_node(member_old, member_new, [*path, member_name])
            else:
                yield from self._handle_node_removed(member_old, [*path, member_name])

    def _check_func(self, func_old: Func, func_new: Func, path: Path) -> Iterator[CompatBreak]:
        if func_old.return_type != func_new.return_type:
            yield TypeChange(node=func_old, old_type=func_old.return_type, new_type=func_new.return_type, path=path)

        for param_name, param_old in func_old.params.items():
            if param_new := func_new.params.get(param_name):
                yield from self._check_param(param_old, param_new, [*path, param_name])
            else:
                yield from self._handle_node_removed(param_old, [*path, param_name])

    def _check_param(self, param_old: Param, param_new: Param, path: Path) -> Iterator[CompatBreak]:
        if param_old.type != param_new.type:
            yield TypeChange(node=param_old, old_type=param_old.type, new_type=param_new.type, path=path)

    def _check_const(self, const_old: Const, const_new: Const, path: Path) -> Iterator[CompatBreak]:
        if const_old.type != const_new.type:
            yield TypeChange(node=const_old, old_type=const_old.type, new_type=const_new.type, path=path)

    def _handle_node_removed(self, node_old: Node, path: Path) -> Iterator[CompatBreak]:
        match node_old:
            case Mod():
                yield Removal(node=node_old, path=path)
            case Func():
                yield Removal(node=node_old, path=path)
            case Param():
                yield Removal(node=node_old, path=path)
            case Const():
                yield Removal(node=node_old, path=path)
            case _:
                msg = f"Checking for {type(node_old)} nodes is not implemented"
                raise NotImplementedError(msg)
