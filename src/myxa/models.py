import logging
import re
from enum import StrEnum
from typing import Literal, Optional, Self, Union

from pydantic import BaseModel, Field

from myxa.errors import UserError

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
    package_name: str
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


class Dep(BaseModel):
    name: str
    version: Version


class PackageInfo(BaseModel):
    name: str
    description: str
    version: Version
    deps: dict[str, Dep]


class PackageLock(BaseModel):
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
