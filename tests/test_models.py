import re

import pytest

from myxa.errors import UserError
from myxa.models import Const, Func, Index, Int, Param, Version, get_node_type_str


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
