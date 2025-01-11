from copy import deepcopy

import pytest

from myxa.checker import Checker, MemberNodeChange, Removal, VarNodeChange
from myxa.errors import InternalError
from myxa.models import Const, Float, Func, Int, Package, Param


class TestChecker:
    def test_check_unchanged(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        breaks = checker.diff(euler_package, euler_package)
        assert len(breaks) == 0

    def test_check_node_type_invalid(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members["add"] = Int()

        with pytest.raises(InternalError, match="Invalid MemberNode type <class 'myxa.models.Int'>"):
            checker.diff(euler_package, euler_package_new)

    def test_check_node_type_changed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members["add"] = Const(
            name="add",
            var_node=Int(),
        )

        breaks = checker.diff(euler_package, euler_package_new)
        assert len(breaks) == 1
        assert isinstance(breaks[0], MemberNodeChange)
        assert isinstance(breaks[0].old_member_node, Func)
        assert isinstance(breaks[0].new_member_node, Const)
        assert breaks[0].path == ["euler", "math", "add"]

    def test_check_function_param_type_changed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members["add"].params["a"] = Param(
            name="a",
            var_node=Float(),
        )

        breaks = checker.diff(euler_package, euler_package_new)
        assert len(breaks) == 1
        assert isinstance(breaks[0], VarNodeChange)
        assert breaks[0].old_var_node == Int()
        assert breaks[0].new_var_node == Float()
        assert breaks[0].path == ["euler", "math", "add", "a"]

    def test_check_function_return_type_changed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        float_add = Func(
            name="add",
            params={
                "a": Param(name="a", var_node=Int()),
                "b": Param(name="b", var_node=Int()),
            },
            return_var_node=Float(),
        )
        euler_package_new.members["math"].members["add"] = float_add

        breaks = checker.diff(euler_package, euler_package_new)
        assert len(breaks) == 1
        assert isinstance(breaks[0], VarNodeChange)
        assert breaks[0].old_var_node == Int()
        assert breaks[0].new_var_node == Float()
        assert breaks[0].path == ["euler", "math", "add"]

    def test_check_const_type_changed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members["pi"] = Const(
            name="pi",
            var_node=Int(),
        )

        breaks = checker.diff(euler_package, euler_package_new)
        assert len(breaks) == 1
        assert isinstance(breaks[0], VarNodeChange)
        assert breaks[0].old_var_node == Float()
        assert breaks[0].new_var_node == Int()
        assert breaks[0].path == ["euler", "math", "pi"]

    def test_check_module_removed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members.pop("math")

        breaks = checker.diff(euler_package, euler_package_new)
        assert len(breaks) == 1
        assert isinstance(breaks[0], Removal)
        assert breaks[0].path == ["euler", "math"]

    def test_check_function_removed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members.pop("add")

        breaks = checker.diff(euler_package, euler_package_new)
        assert len(breaks) == 1
        assert isinstance(breaks[0], Removal)
        assert breaks[0].path == ["euler", "math", "add"]

    def test_check_param_removed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members["add"].params.pop("a")

        breaks = checker.diff(euler_package, euler_package_new)
        assert len(breaks) == 1
        assert isinstance(breaks[0], Removal)
        assert breaks[0].path == ["euler", "math", "add", "a"]

    def test_check_const_removed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members.pop("pi")

        breaks = checker.diff(euler_package, euler_package_new)
        assert len(breaks) == 1
        assert isinstance(breaks[0], Removal)
        assert breaks[0].path == ["euler", "math", "pi"]

    def test_check_return_type_of_func_return_type_changed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_old = deepcopy(euler_package)
        euler_package_old.members["math"].members["add"].return_var_node = Func(
            name="add_curry",
            params={},
            return_var_node=Int(),
        )

        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members["add"].return_var_node = Func(
            name="add_curry",
            params={},
            return_var_node=Float(),
        )

        breaks = checker.diff(euler_package_old, euler_package_new)
        assert len(breaks) == 1
        assert isinstance(breaks[0], VarNodeChange)
        assert isinstance(breaks[0].tree_node, Func)
        assert breaks[0].tree_node.name == "add_curry"
        assert breaks[0].old_var_node.node_type == "int"
        assert breaks[0].new_var_node.node_type == "float"
        assert breaks[0].path == ["euler", "math", "add", "add_curry"]
