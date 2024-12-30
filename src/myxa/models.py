import logging
import re
from copy import deepcopy
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

    def add_package(self, package: Package) -> None:
        package = deepcopy(package)
        version_str = package.info.version.to_str()
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
            if version.to_str() in namespace.packages:
                del namespace.packages[version.to_str()]
            else:
                msg = (
                    f"Package {package.info.name} version {version.to_str()}"
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
        if package := namespace.packages.get(version.to_str()):
            return package
        msg = f"Package {package_name}=={version.to_str()} not found in the provided index: {self.name}"
        raise UserError(msg)

    def get_latest_package(self, package_name: str) -> Package:
        namespace = self.get_namespace(package_name)
        versions = [Version.from_str(s) for s in namespace.packages]
        latest_version = max(versions)
        version_str = latest_version.to_str()
        return namespace.packages[version_str]
