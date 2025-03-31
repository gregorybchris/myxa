from __future__ import annotations

import logging

from pydantic import BaseModel

from myxa.version import Version

logger = logging.getLogger(__name__)


class Dependency(BaseModel):
    name: str
    version: Version

    @classmethod
    def new(cls, name: str, version_str: str) -> Dependency:
        version = Version.new(version_str)
        return cls(name=name, version=version)

    def is_satisfied_by(self, version: Version) -> bool:
        return version.major == self.version.major and version.minor >= self.version.minor

    def __str__(self) -> str:
        return f"{self.name}~={self.version}"
