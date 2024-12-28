import pytest

from myxa.main import Const, Func, Import, Index, Mod, Package, PackageInfo, Param, Type, Version


@pytest.fixture(name="euler_package")
def euler_package_fixture() -> Package:
    return Package(
        info=PackageInfo(
            name="euler",
            description="A compilation of useful math stuff",
            version=Version(major=0, minor=1),
        ),
        members={
            "math": Mod(
                name="math",
                imports=[],
                members={
                    "pi": Const(name="pi", type=Type.Float),
                    "e": Const(name="e", type=Type.Float),
                    "add": Func(
                        name="add",
                        params={
                            "a": Param(name="a", type=Type.Int),
                            "b": Param(name="b", type=Type.Int),
                        },
                        return_type=Type.Int,
                    ),
                    "sub": Func(
                        name="sub",
                        params={
                            "a": Param(name="a", type=Type.Int),
                            "b": Param(name="b", type=Type.Int),
                        },
                        return_type=Type.Int,
                    ),
                    "trig": Mod(
                        name="trig",
                        imports=[],
                        members={
                            "sin": Func(
                                name="sin",
                                params={"x": Param(name="x", type=Type.Float)},
                                return_type=Type.Float,
                            ),
                            "cos": Func(
                                name="cos",
                                params={"x": Param(name="x", type=Type.Float)},
                                return_type=Type.Float,
                            ),
                            "tan": Func(
                                name="tan",
                                params={"x": Param(name="x", type=Type.Float)},
                                return_type=Type.Float,
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
            version=Version(major=2, minor=0),
        ),
        members={
            "serialize": Func(
                name="serialize",
                params={
                    "data": Param(name="s", type=Type.Str),
                },
                return_type=Type.Str,
            ),
            "deserialize": Func(
                name="deserialize",
                params={
                    "data": Param(name="s", type=Type.Str),
                },
                return_type=Type.Str,
            ),
        },
    )


@pytest.fixture(name="interlet_package")
def interlet_package_fixture() -> Package:
    return Package(
        info=PackageInfo(
            name="interlet",
            description="A blazingly fast webserver",
            version=Version(major=3, minor=4),
        ),
        members={
            "router": Mod(
                name="router",
                imports=[Import(path=["flatty"], member_names=["serialize", "deserialize"])],
                members={
                    "serve": Func(
                        name="serve",
                        params={
                            "host": Param(name="host", type=Type.Str),
                            "port": Param(name="port", type=Type.Int),
                        },
                        return_type=Type.Null,
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
            version=Version(major=1, minor=2),
        ),
        members={
            "main": Mod(
                name="main",
                imports=[
                    Import(path=["euler", "math"], member_names=["add"]),
                    Import(path=["interlet", "router"], member_names=["serve"]),
                ],
                members={
                    "run": Func(
                        name="run",
                        params={},
                        return_type=Type.Null,
                    )
                },
            )
        },
    )


@pytest.fixture(name="primary_index")
def primary_index_fixture() -> Index:
    return Index(name="primary")
