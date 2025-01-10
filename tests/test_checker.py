from copy import deepcopy

import pytest

from myxa.checker import Checker, Removal, TreeNodeChange, VarNodeChange
from myxa.errors import InternalError
from myxa.models import Const, Float, Func, Int, Package, Param


class TestChecker:
    def test_check_unchanged(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        compat_breaks = checker.diff(euler_package, euler_package)
        assert len(compat_breaks) == 0

    def test_check_node_type_invalid(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members["add"] = Int()

        with pytest.raises(InternalError, match="Invalid node type <class 'myxa.models.Int'>, not permitted"):
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

        compat_breaks = checker.diff(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], TreeNodeChange)
        assert isinstance(compat_breaks[0].old_tree_node, Func)
        assert isinstance(compat_breaks[0].new_tree_node, Const)
        assert compat_breaks[0].path == ["euler", "math", "add"]

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

        compat_breaks = checker.diff(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], VarNodeChange)
        assert compat_breaks[0].old_var_node == Int()
        assert compat_breaks[0].new_var_node == Float()
        assert compat_breaks[0].path == ["euler", "math", "add", "a"]

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

        compat_breaks = checker.diff(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], VarNodeChange)
        assert compat_breaks[0].old_var_node == Int()
        assert compat_breaks[0].new_var_node == Float()
        assert compat_breaks[0].path == ["euler", "math", "add"]

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

        compat_breaks = checker.diff(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], VarNodeChange)
        assert compat_breaks[0].old_var_node == Float()
        assert compat_breaks[0].new_var_node == Int()
        assert compat_breaks[0].path == ["euler", "math", "pi"]

    def test_check_module_removed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members.pop("math")

        compat_breaks = checker.diff(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], Removal)
        assert compat_breaks[0].path == ["euler", "math"]

    def test_check_function_removed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members.pop("add")

        compat_breaks = checker.diff(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], Removal)
        assert compat_breaks[0].path == ["euler", "math", "add"]

    def test_check_param_removed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members["add"].params.pop("a")

        compat_breaks = checker.diff(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], Removal)
        assert compat_breaks[0].path == ["euler", "math", "add", "a"]

    def test_check_const_removed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members.pop("pi")

        compat_breaks = checker.diff(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], Removal)
        assert compat_breaks[0].path == ["euler", "math", "pi"]
