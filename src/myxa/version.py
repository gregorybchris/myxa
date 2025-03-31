from __future__ import annotations

import logging
import re

from pydantic import BaseModel

from myxa.errors import UserError

logger = logging.getLogger(__name__)


class Version(BaseModel):
    major: int
    minor: int

    @classmethod
    def new(cls, version_str: str) -> Version:
        if not re.match(r"\d+\.\d+", version_str):
            msg = f"Invalid version string: {version_str}"
            raise UserError(msg)
        parts = version_str.split(".")
        major = int(parts[0])
        minor = int(parts[1])
        return cls(major=major, minor=minor)

    @classmethod
    def default(cls) -> Version:
        return cls(major=0, minor=1)

    def next_minor(self) -> "Version":
        return Version(major=self.major, minor=self.minor + 1)

    def next_major(self) -> "Version":
        return Version(major=self.major + 1, minor=0)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"

    def __hash__(self) -> int:
        return hash(str(self))

    def __lt__(self, other: Version) -> bool:
        if self.major < other.major:
            return True
        if self.major == other.major:
            return self.minor < other.minor
        return False
