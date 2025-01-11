import re

import pytest

from myxa.errors import UserError
from myxa.models import Const, Enum, Field, Func, Index, Int, Null, Param, Struct, Variant, Version, get_node_type_str


class TestModels:
    def test_version_invalid_from_str_raises_user_error(self) -> None:
        with pytest.raises(UserError, match="Invalid version string: 100"):
            Version.from_str("100")

    def test_package_not_found_in_index_raises_user_error(
        self,
        primary_index: Index,
    ) -> None:
        with pytest.raises(UserError, match=re.escape("Package euler not found in the provided index: primary")):
            primary_index.get_namespace("euler")

    def test_get_node_type_str_const_int(self) -> None:
        const_node = Const(name="pi", var_node=Int())
        const_node_str = get_node_type_str(const_node)
        assert const_node_str == "Const[Int]"

    def test_get_node_type_str_func(self) -> None:
        func_node = Func(
            name="add",
            params={
                "a": Param(name="a", var_node=Int()),
            },
            return_var_node=Func(
                name="curried_add",
                params={
                    "b": Param(name="b", var_node=Int()),
                },
                return_var_node=Int(),
            ),
        )

        func_node_str = get_node_type_str(func_node)
        assert func_node_str == "Func[[Int], Func[[Int], Int]]"

    def test_get_node_type_str_const_func(self) -> None:
        func_node = Func(
            name="add",
            params={
                "a": Param(name="a", var_node=Int()),
                "b": Param(name="b", var_node=Int()),
            },
            return_var_node=Int(),
        )
        const_node = Const(name="add", var_node=func_node)
        const_node_str = get_node_type_str(const_node)
        assert const_node_str == "Const[Func[[Int, Int], Int]]"

    def test_get_node_type_str_enum(self) -> None:
        enum_node = Enum(
            name="Color",
            variants={
                "Red": Variant(name="Red", var_node=Int()),
                "Green": Variant(name="Green", var_node=Int()),
                "Blue": Variant(name="Blue", var_node=Int()),
            },
        )
        enum_node_str = get_node_type_str(enum_node)
        assert enum_node_str == "Enum(Color)[Red(Int), Green(Int), Blue(Int)]"

    def test_get_node_type_str_enum_with_nulls(self) -> None:
        enum_node = Enum(
            name="Parity",
            variants={
                "Odd": Variant(name="Odd", var_node=Null()),
                "Even": Variant(name="Even", var_node=Null()),
            },
        )
        enum_node_str = get_node_type_str(enum_node)
        assert enum_node_str == "Enum(Parity)[Odd, Even]"

    def test_get_node_type_str_struct(self) -> None:
        enum_node = Struct(
            name="Generator",
            fields={
                "mod": Field(name="mod", var_node=Int()),
                "mult": Field(name="mult", var_node=Int()),
                "inc": Field(name="inc", var_node=Int()),
            },
        )
        enum_node_str = get_node_type_str(enum_node)
        assert enum_node_str == "Struct(Generator)[mod(Int), mult(Int), inc(Int)]"
