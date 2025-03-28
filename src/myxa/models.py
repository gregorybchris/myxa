import logging
import re
from copy import deepcopy
from typing import Literal, Optional, Self, Union

from pydantic import BaseModel
from pydantic import Field as PydanticField

from myxa.errors import UserError

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
    var_node: "VarNode"


class Maybe(BaseModel):
    node_type: Literal["maybe"] = "maybe"
    var_node: "VarNode"


class List(BaseModel):
    node_type: Literal["list"] = "list"
    var_node: "VarNode"


class Set(BaseModel):
    node_type: Literal["set"] = "set"
    var_node: "VarNode"


class Dict(BaseModel):
    node_type: Literal["dict"] = "dict"
    key_var_node: "VarNode"
    val_var_node: "VarNode"


class Param(BaseModel):
    node_type: Literal["param"] = "param"
    name: str
    var_node: "VarNode"


class Func(BaseModel):
    node_type: Literal["func"] = "func"
    name: str
    params: dict[str, Param]
    return_var_node: "VarNode"


class Field(BaseModel):
    node_type: Literal["field"] = "field"
    name: str
    var_node: "VarNode"


class Struct(BaseModel):
    node_type: Literal["struct"] = "struct"
    name: str
    fields: dict[str, Field]


class Variant(BaseModel):
    node_type: Literal["variant"] = "variant"
    name: str
    var_node: "VarNode"


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
    members: dict[str, "MemberNode"]


# Nodes that can be declared at the top level of package modules
MemberNode = Union[Const, Enum, Func, Mod, Struct]

# Nodes that can be referred to in a package diff
TreeNode = Union[Const, Enum, Field, Func, Mod, Param, Struct, Variant]

# Nodes that be passed as a type
VarNode = Union[Bool, Dict, Enum, Float, Func, Int, List, Maybe, Null, Set, Str, Struct]

# All node types
Node = Union[MemberNode, TreeNode, VarNode]


class Version(BaseModel):
    major: int
    minor: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"

    @classmethod
    def default(cls) -> Self:
        return cls(major=0, minor=1)

    @classmethod
    def from_str(cls, s: str) -> Self:
        if not re.match(r"\d+\.\d+", s):
            msg = f"Invalid version string: {s}"
            raise UserError(msg)
        parts = s.split(".")
        major = int(parts[0])
        minor = int(parts[1])
        return cls(major=major, minor=minor)

    def __hash__(self) -> int:
        return hash(str(self))

    def __lt__(self, other: Self) -> bool:
        if self.major < other.major:
            return True
        if self.major == other.major:
            return self.minor < other.minor
        return False

    def next_minor(self) -> "Version":
        return Version(major=self.major, minor=self.minor + 1)

    def next_major(self) -> "Version":
        return Version(major=self.major + 1, minor=0)


class Dep(BaseModel):
    name: str
    version: Version


class PackageInfo(BaseModel):
    name: str
    description: str
    version: Version
    deps: dict[str, Dep]


class PackageLock(BaseModel):
    deps: dict[str, Dep] = PydanticField(default_factory=dict)


class Package(BaseModel):
    info: PackageInfo
    lock: Optional[PackageLock] = None
    members: dict[str, MemberNode]


class Namespace(BaseModel):
    name: str
    packages: dict[str, Package] = PydanticField(default_factory=dict)


class Index(BaseModel):
    name: str
    namespaces: dict[str, Namespace] = PydanticField(default_factory=dict)

    def add_package(self, package: Package) -> None:
        package = deepcopy(package)
        version_str = str(package.info.version)
        if namespace := self.namespaces.get(package.info.name):
            if version_str in namespace.packages:
                msg = f"Package {package.info.name}=={version_str} already exists in provided index: {self.name}"
                raise UserError(msg)
            namespace.packages[version_str] = package
        else:
            namespace = Namespace(name=package.info.name)
            namespace.packages[version_str] = package
            self.namespaces[package.info.name] = namespace

    def remove_package(self, package: Package, version: Version) -> None:
        if namespace := self.namespaces.get(package.info.name):
            if str(version) in namespace.packages:
                del namespace.packages[str(version)]
                if len(namespace.packages) == 0:
                    del self.namespaces[package.info.name]
            else:
                msg = (
                    f"Package {package.info.name} version {version!s}"
                    f" not found in index {self.name}, unable to yank"
                )
                raise UserError(msg)
        else:
            msg = f"Package {package.info.name} not found in index {self.name}, unable to yank"
            raise UserError(msg)

    def get_namespace(self, package_name: str) -> Namespace:
        if namespace := self.namespaces.get(package_name):
            return namespace
        msg = f"Package {package_name} not found in the provided index: {self.name}"
        raise UserError(msg)

    def list_versions(self, package_name: str) -> list[Version]:
        namespace = self.get_namespace(package_name)
        return [package.info.version for package in namespace.packages.values()]

    def get_package(self, package_name: str, version: Version) -> Package:
        namespace = self.get_namespace(package_name)
        if package := namespace.packages.get(str(version)):
            return package
        msg = f"Package {package_name}=={version!s} not found in the provided index: {self.name}"
        raise UserError(msg)

    def get_latest_package(self, package_name: str) -> Package:
        namespace = self.get_namespace(package_name)
        versions = [Version.from_str(s) for s in namespace.packages]
        latest_version = max(versions)
        version_str = str(latest_version)
        return namespace.packages[version_str]
