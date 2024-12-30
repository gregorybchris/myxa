from copy import deepcopy

import pytest

from myxa.checker import Checker, NodeTypeChange, Removal, TypeChange
from myxa.errors import InternalError
from myxa.models import Const, Func, Package, Param, Type


class TestChecker:
    def test_check_unchanged(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        compat_breaks = checker.check(euler_package, euler_package)
        assert len(compat_breaks) == 0

    def test_check_node_type_invalid(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members["add"] = Type.Int

        with pytest.raises(InternalError, match="Invalid node type <enum 'Type'>, not permitted"):
            checker.check(euler_package, euler_package_new)

    def test_check_node_type_changed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members["add"] = Const(
            name="add",
            type=Type.Int,
        )

        compat_breaks = checker.check(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], NodeTypeChange)
        assert isinstance(compat_breaks[0].old_node, Func)
        assert isinstance(compat_breaks[0].new_node, Const)
        assert compat_breaks[0].path == ["euler", "math", "add"]

    def test_check_function_param_type_changed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members["add"].params["a"] = Param(
            name="a",
            type=Type.Float,
        )

        compat_breaks = checker.check(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], TypeChange)
        assert compat_breaks[0].old_type == Type.Int
        assert compat_breaks[0].new_type == Type.Float
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
                "a": Param(name="a", type=Type.Int),
                "b": Param(name="b", type=Type.Int),
            },
            return_type=Type.Float,
        )
        euler_package_new.members["math"].members["add"] = float_add

        compat_breaks = checker.check(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], TypeChange)
        assert compat_breaks[0].old_type == Type.Int
        assert compat_breaks[0].new_type == Type.Float
        assert compat_breaks[0].path == ["euler", "math", "add"]

    def test_check_const_type_changed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members["math"].members["pi"] = Const(
            name="pi",
            type=Type.Int,
        )

        compat_breaks = checker.check(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], TypeChange)
        assert compat_breaks[0].old_type == Type.Float
        assert compat_breaks[0].new_type == Type.Int
        assert compat_breaks[0].path == ["euler", "math", "pi"]

    def test_check_module_removed(
        self,
        checker: Checker,
        euler_package: Package,
    ) -> None:
        euler_package_new = deepcopy(euler_package)
        euler_package_new.members.pop("math")

        compat_breaks = checker.check(euler_package, euler_package_new)
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

        compat_breaks = checker.check(euler_package, euler_package_new)
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

        compat_breaks = checker.check(euler_package, euler_package_new)
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

        compat_breaks = checker.check(euler_package, euler_package_new)
        assert len(compat_breaks) == 1
        assert isinstance(compat_breaks[0], Removal)
        assert compat_breaks[0].path == ["euler", "math", "pi"]
