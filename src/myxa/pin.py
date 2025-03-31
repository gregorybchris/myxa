from __future__ import annotations

import logging

from pydantic import BaseModel

from myxa.version import Version

logger = logging.getLogger(__name__)


class Pin(BaseModel):
    name: str
    version: Version

    @classmethod
    def new(cls, name: str, version_str: str) -> Pin:
        version = Version.new(version_str)
        return Pin(name=name, version=version)

    def __str__(self) -> str:
        return f"{self.name}=={self.version}"
