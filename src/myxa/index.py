from __future__ import annotations

import logging
from copy import deepcopy

from pydantic import BaseModel, Field

from myxa.errors import UserError
from myxa.package import Package  # noqa: TC001
from myxa.version import Version

logger = logging.getLogger(__name__)


class Namespace(BaseModel):
    name: str
    packages: dict[str, Package] = Field(default_factory=dict)


class Index(BaseModel):
    name: str
    namespaces: dict[str, Namespace] = Field(default_factory=dict)

    def add(self, package: Package) -> None:
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

    def remove(self, package: Package, version: Version) -> None:
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

    def _get_namespace(self, name: str) -> Namespace:
        if namespace := self.namespaces.get(name):
            return namespace
        msg = f"Package {name} not found in the provided index: {self.name}"
        raise UserError(msg)

    def list_versions_sorted(self, name: str) -> list[Package]:
        namespace = self._get_namespace(name)
        return sorted(namespace.packages.values(), reverse=True, key=lambda p: p.info.version)

    def get(self, name: str, version: Version) -> Package:
        namespace = self._get_namespace(name)
        if package := namespace.packages.get(str(version)):
            return package
        msg = f"Package {name}=={version!s} not found in the provided index: {self.name}"
        raise UserError(msg)

    def get_latest(self, name: str) -> Package:
        namespace = self._get_namespace(name)
        versions = [Version.new(s) for s in namespace.packages]
        latest_version = max(versions)
        version_str = str(latest_version)
        return namespace.packages[version_str]
