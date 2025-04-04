from __future__ import annotations

import logging
from copy import deepcopy
from typing import Iterator, Optional

from pydantic import BaseModel, Field

from myxa.dependency import Dependency
from myxa.nodes import MemberNode  # noqa: TC001
from myxa.pin import Pin
from myxa.version import Version

logger = logging.getLogger(__name__)


class Info(BaseModel):
    name: str
    version: Version
    description: Optional[str] = None

    @classmethod
    def new(cls, name: str, version_str: str) -> Info:
        version = Version.new(version_str)
        return cls(name=name, version=version)


class Dependencies(BaseModel):
    direct: dict[str, Dependency] = Field(default_factory=dict)

    @classmethod
    def new(cls, dependencies: list[Dependency]) -> Dependencies:
        direct_dict = {dependency.name: dependency for dependency in dependencies}
        return cls(direct=direct_dict)

    def get(self, name: str) -> Optional[Dependency]:
        return self.direct.get(name)

    def has(self, name: str) -> bool:
        return name in self.direct

    def add(self, dependency: Dependency) -> None:
        self.direct[dependency.name] = dependency

    def pop(self, name: str) -> Optional[Dependency]:
        return self.direct.pop(name, None)

    def list_alphabetical(self) -> list[Dependency]:
        return sorted(self.direct.values(), key=lambda dep: dep.name)

    def list(self) -> list[Dependency]:
        return list(self.direct.values())

    def __len__(self) -> int:
        return len(self.direct)


class Lock(BaseModel):
    pins: dict[str, Pin] = Field(default_factory=dict)
    children: dict[str, list[str]] = Field(default_factory=dict)
    sources: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def new(
        cls,
        pins: list[Pin],
        children: Optional[dict[str, list[str]]] = None,
        sources: Optional[dict[str, str]] = None,
    ) -> Lock:
        pins_dict = {pin.name: pin for pin in pins}
        return cls(pins=pins_dict, children=children or {}, sources=sources or {})

    def has(self, name: str) -> bool:
        return name in self.pins

    def get(self, name: str) -> Optional[Pin]:
        return self.pins.get(name)

    def iter(self) -> Iterator[Pin]:
        return iter(self.pins.values())

    def list_alphabetical(self) -> list[Pin]:
        return sorted(self.pins.values(), key=lambda pin: pin.name)

    def add(self, pin: Pin) -> None:
        self.pins[pin.name] = pin

    def add_child(self, parent_name: str, name: str) -> None:
        if parent_name not in self.children:
            self.children[parent_name] = []
        self.children[parent_name].append(name)

    def add_source(self, name: str, source_name: str) -> None:
        self.sources[name] = source_name

    def remove(self, name: str) -> None:
        del self.pins[name]

    def clone_add(self, pin: Pin, *, parent_name: str, source_name: str) -> Lock:
        new_lock = deepcopy(self)
        new_lock.add(pin)
        new_lock.add_child(parent_name, pin.name)
        new_lock.add_source(pin.name, source_name)
        return new_lock

    def is_compatible_with(self, package: Package) -> bool:
        if pin := self.get(package.info.name):  # noqa: SIM102
            if pin.version != package.info.version:
                return False

        return True

    def __getitem__(self, name: str) -> Pin:
        return self.pins[name]

    def __len__(self) -> int:
        return len(self.pins)

    def __str__(self) -> str:
        if len(self.pins) == 0:
            return "<empty>"
        return "<" + ", ".join(str(pin) for pin in self.iter()) + ">"


class Members(BaseModel):
    nodes: dict[str, MemberNode] = Field(default_factory=dict)

    def pop(self, name: str) -> Optional[MemberNode]:
        return self.nodes.pop(name, None)

    def list(self) -> list[MemberNode]:
        return list(self.nodes.values())

    def to_dict(self) -> dict[str, MemberNode]:
        return self.nodes

    def __getitem__(self, name: str) -> MemberNode:
        return self.nodes[name]


class Package(BaseModel):
    info: Info
    dependencies: Dependencies = Field(default_factory=Dependencies)
    lock: Optional[Lock] = None
    members: Members = Field(default_factory=Members)

    @classmethod
    def new(cls, name: str, version_str: str, dependencies: list[tuple[str, str]]) -> Package:
        info = Info.new(name=name, version_str=version_str)
        dependencies_list = [Dependency.new(dep_name, dep_version) for dep_name, dep_version in dependencies]
        return cls(info=info, dependencies=Dependencies.new(dependencies_list))

    def to_pin(self) -> Pin:
        return Pin(name=self.info.name, version=self.info.version)

    def __str__(self) -> str:
        return f"{self.info.name}=={self.info.version}"
