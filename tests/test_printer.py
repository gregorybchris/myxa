import re
from copy import deepcopy

import pytest
from rich.console import Console

from myxa.checker import Checker
from myxa.manager import Manager
from myxa.models import Const, Index, Package, PackageLock, Type
from myxa.printer import Printer


@pytest.fixture(scope="module", name="printer")
def printer_fixture() -> Printer:
    console = Console()
    return Printer(console=console)


def clean_colors(text: str) -> str:
    ansi_escape = re.compile(r"\x1b\[.*?m")
    return ansi_escape.sub("", text)


class TestPrinter:
    @pytest.mark.parametrize("show_deps", [True, False])
    @pytest.mark.parametrize("show_lock", [True, False])
    @pytest.mark.parametrize("show_interface", [True, False])
    def test_print_package(  # noqa: PLR0913
        self,
        printer: Printer,
        euler_package: Package,
        show_deps: bool,
        show_lock: bool,
        show_interface: bool,
        capsys: pytest.CaptureFixture,
    ) -> None:
        euler_package.lock = PackageLock(deps=euler_package.info.deps)
        printer.print_package(
            euler_package,
            show_deps=show_deps,
            show_lock=show_lock,
            show_interface=show_interface,
        )

        capture_result = capsys.readouterr()
        text_output = clean_colors(capture_result.out)

        assert euler_package.info.name in text_output
        assert euler_package.info.version.to_str() in text_output
        assert euler_package.info.description in text_output

        if show_deps:
            assert "Dependencies" in text_output
            assert "[none]" in text_output
        else:
            assert "Dependencies" not in text_output

        if show_lock:
            assert "Locked dependencies" in text_output
            assert "[none]" in text_output
        else:
            assert "Locked dependencies" not in text_output

        if show_interface:
            assert "Interface" in text_output
            assert "add(" in text_output
            assert "pi" in text_output
        else:
            assert "Interface" not in text_output

    @pytest.mark.parametrize("show_versions", [True, False])
    def test_print_index(  # noqa: PLR0913
        self,
        printer: Printer,
        manager: Manager,
        app_package: Package,
        euler_package: Package,
        primary_index: Index,
        show_versions: bool,
        capsys: pytest.CaptureFixture,
    ) -> None:
        manager.lock(euler_package, primary_index)
        manager.publish(euler_package, primary_index, interactive=False)
        manager.lock(app_package, primary_index)
        manager.publish(app_package, primary_index, interactive=False)

        printer.print_index(primary_index, show_versions=show_versions)

        capture_result = capsys.readouterr()
        text_output = clean_colors(capture_result.out)

        if show_versions:
            expected = ["euler==0.1", "app==0.1"]
            assert all(text in text_output for text in expected)
        else:
            expected = ["euler", "app"]
            assert all(text in text_output for text in expected)

    def test_print_lock_diff(  # noqa: PLR0913
        self,
        printer: Printer,
        manager: Manager,
        interlet_package: Package,
        flatty_package: Package,
        euler_package: Package,
        primary_index: Index,
        capsys: pytest.CaptureFixture,
    ) -> None:
        manager.lock(flatty_package, primary_index)
        manager.publish(flatty_package, primary_index, interactive=False)
        manager.add(interlet_package, flatty_package.info.name, primary_index)

        manager.lock(interlet_package, primary_index)
        old_lock = interlet_package.lock

        manager.lock(euler_package, primary_index)
        manager.publish(euler_package, primary_index, interactive=False)

        manager.add(interlet_package, "euler", primary_index)
        manager.remove(interlet_package, flatty_package.info.name)
        manager.lock(interlet_package, primary_index)
        new_lock = interlet_package.lock

        printer.print_lock_diff(old_lock, new_lock)

        capture_result = capsys.readouterr()
        text_output = clean_colors(capture_result.out)

        expected = """Project lock updated with 1 addition and 1 removal
+ euler~=0.1
- flatty~=0.1
"""
        assert expected in text_output

    def test_print_breaks(
        self,
        printer: Printer,
        euler_package: Package,
        checker: Checker,
        capsys: pytest.CaptureFixture,
    ) -> None:
        original_package = deepcopy(euler_package)
        euler_package.members["math"].members["pi"].type = Type.Str
        del euler_package.members["math"].members["e"]
        euler_package.members["math"].members["add"].params["a"].type = Type.Float
        euler_package.members["math"].members["sub"] = Const(name="sub", type=Type.Int)
        del euler_package.members["math"].members["trig"]

        compat_breaks = checker.check(original_package, euler_package)
        printer.print_breaks(compat_breaks, original_package)

        capture_result = capsys.readouterr()
        text_output = clean_colors(capture_result.out)

        expected = """Found 5 compatibility breaks compared to euler==0.1
- The type of Const 'euler.math.pi' has changed from Float to Str
- Const 'euler.math.e' has been removed
- The type of Param 'euler.math.add.a' has changed from Int to Float
- The type of 'euler.math.sub' has changed from Func to Const
- Mod 'euler.math.trig' has been removed
"""
        assert text_output == expected
