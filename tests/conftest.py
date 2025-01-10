import pytest

from myxa.checker import Checker
from myxa.manager import Manager
from myxa.models import Const, Float, Func, Import, Index, Int, Mod, Null, Package, PackageInfo, Param, Str, Version
from myxa.resolver import Resolver


@pytest.fixture(name="euler_package")
def euler_package_fixture() -> Package:
    return Package(
        info=PackageInfo(
            name="euler",
            description="A compilation of useful math stuff",
            version=Version.from_str("0.1"),
            deps={},
        ),
        members={
            "math": Mod(
                name="math",
                imports=[],
                members={
                    "pi": Const(name="pi", var_node=Float()),
                    "e": Const(name="e", var_node=Float()),
                    "add": Func(
                        name="add",
                        params={
                            "a": Param(name="a", var_node=Int()),
                            "b": Param(name="b", var_node=Int()),
                        },
                        return_var_node=Int(),
                    ),
                    "sub": Func(
                        name="sub",
                        params={
                            "a": Param(name="a", var_node=Int()),
                            "b": Param(name="b", var_node=Int()),
                        },
                        return_var_node=Int(),
                    ),
                    "trig": Mod(
                        name="trig",
                        imports=[],
                        members={
                            "sin": Func(
                                name="sin",
                                params={"x": Param(name="x", var_node=Float())},
                                return_var_node=Float(),
                            ),
                            "cos": Func(
                                name="cos",
                                params={"x": Param(name="x", var_node=Float())},
                                return_var_node=Float(),
                            ),
                            "tan": Func(
                                name="tan",
                                params={"x": Param(name="x", var_node=Float())},
                                return_var_node=Float(),
                            ),
                        },
                    ),
                },
            )
        },
    )


@pytest.fixture(name="flatty_package")
def flatty_package_fixture() -> Package:
    return Package(
        info=PackageInfo(
            name="flatty",
            description="A package for serializing and deserializing data",
            version=Version.from_str("2.0"),
            deps={},
        ),
        members={
            "serialize": Func(
                name="serialize",
                params={
                    "data": Param(name="s", var_node=Str()),
                },
                return_var_node=Str(),
            ),
            "deserialize": Func(
                name="deserialize",
                params={
                    "data": Param(name="s", var_node=Str()),
                },
                return_var_node=Str(),
            ),
        },
    )


@pytest.fixture(name="interlet_package")
def interlet_package_fixture() -> Package:
    return Package(
        info=PackageInfo(
            name="interlet",
            description="A blazingly fast webserver",
            version=Version.from_str("3.4"),
            deps={},
        ),
        members={
            "router": Mod(
                name="router",
                imports=[
                    Import(package_name="flatty", path=[], member_names=["serialize", "deserialize"]),
                ],
                members={
                    "serve": Func(
                        name="serve",
                        params={
                            "host": Param(name="host", var_node=Str()),
                            "port": Param(name="port", var_node=Int()),
                        },
                        return_var_node=Null(),
                    )
                },
            )
        },
    )


@pytest.fixture(name="app_package")
def app_package_fixture() -> Package:
    return Package(
        info=PackageInfo(
            name="app",
            description="A fun app for doing math",
            version=Version.from_str("1.2"),
            deps={},
        ),
        members={
            "main": Mod(
                name="main",
                imports=[
                    Import(package_name="euler", path=["math"], member_names=["add"]),
                    Import(package_name="interlet", path=["router"], member_names=["serve"]),
                ],
                members={
                    "run": Func(
                        name="run",
                        params={},
                        return_var_node=Null(),
                    )
                },
            )
        },
    )


@pytest.fixture(name="primary_index")
def primary_index_fixture() -> Index:
    return Index(name="primary")


@pytest.fixture(name="manager", scope="module")
def manager_fixture() -> Manager:
    return Manager()


@pytest.fixture(name="resolver")
def resolver_fixture(primary_index: Index) -> Resolver:
    return Resolver(index=primary_index)


@pytest.fixture(name="checker")
def checker_fixture() -> Checker:
    return Checker()
