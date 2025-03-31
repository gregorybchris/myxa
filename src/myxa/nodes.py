from __future__ import annotations

import logging
from typing import Literal, Union

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Bool(BaseModel):
    node_type: Literal["bool"] = "bool"


class Float(BaseModel):
    node_type: Literal["float"] = "float"


class Int(BaseModel):
    node_type: Literal["int"] = "int"


class Null(BaseModel):
    node_type: Literal["null"] = "null"


class Str(BaseModel):
    node_type: Literal["str"] = "str"


class Const(BaseModel):
    node_type: Literal["const"] = "const"
    name: str
    var_node: VarNode


class Maybe(BaseModel):
    node_type: Literal["maybe"] = "maybe"
    var_node: VarNode


class List(BaseModel):
    node_type: Literal["list"] = "list"
    var_node: VarNode


class Set(BaseModel):
    node_type: Literal["set"] = "set"
    var_node: VarNode


class Dict(BaseModel):
    node_type: Literal["dict"] = "dict"
    key_var_node: VarNode
    val_var_node: VarNode


class Tuple(BaseModel):
    node_type: Literal["tuple"] = "tuple"
    var_nodes: list[VarNode]


class Param(BaseModel):
    node_type: Literal["param"] = "param"
    name: str
    var_node: VarNode


class Func(BaseModel):
    node_type: Literal["func"] = "func"
    name: str
    params: dict[str, Param]
    return_var_node: VarNode


class Field(BaseModel):
    node_type: Literal["field"] = "field"
    name: str
    var_node: VarNode


class Struct(BaseModel):
    node_type: Literal["struct"] = "struct"
    name: str
    fields: dict[str, Field]


class Variant(BaseModel):
    node_type: Literal["variant"] = "variant"
    name: str
    var_node: VarNode


class Enum(BaseModel):
    node_type: Literal["enum"] = "enum"
    name: str
    variants: dict[str, Variant]


class Import(BaseModel):
    package_name: str
    path: list[str]
    member_names: list[str]


class Mod(BaseModel):
    node_type: Literal["mod"] = "mod"
    name: str
    imports: list[Import]
    members: dict[str, MemberNode]


# Nodes that can be declared at the top level of package modules
MemberNode = Union[Const, Enum, Func, Mod, Struct]

# Nodes that can be referred to in a package diff
TreeNode = Union[Const, Enum, Field, Func, Mod, Param, Struct, Variant]

# Nodes that be passed as a type
VarNode = Union[Bool, Dict, Enum, Float, Func, Int, List, Maybe, Null, Set, Str, Struct, Tuple]

# All node types
Node = Union[MemberNode, TreeNode, VarNode]
