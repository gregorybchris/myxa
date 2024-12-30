import re
from copy import deepcopy

import pytest
from rich.console import Console

from myxa.checker import Checker
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
    @pytest.mark.parametrize("show_modules", [True, False])
    def test_print_package(
        self,
        printer: Printer,
        app_package: Package,
        show_deps: bool,
        show_lock: bool,
        show_modules: bool,
    ) -> None:
        app_package.lock = PackageLock(deps=app_package.info.deps)
        printer.print_package(
            app_package,
            show_deps=show_deps,
            show_lock=show_lock,
            show_modules=show_modules,
        )

    @pytest.mark.parametrize("show_versions", [True, False])
    def test_print_index(
        self,
        printer: Printer,
        primary_index: Index,
        show_versions: bool,
    ) -> None:
        printer.print_index(
            primary_index,
            show_versions=show_versions,
        )

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
        printer.print_breaks(compat_breaks)

        captured = capsys.readouterr()
        text_output = clean_colors(captured.out)

        expected = """Found 5 compatibility breaks
- The type of Const 'euler.math.pi' has changed from Float to Str
- Const 'euler.math.e' has been removed
- The type of Param 'euler.math.add.a' has changed from Int to Float
- The type of 'euler.math.sub' has changed from Func to Const
- Mod 'euler.math.trig' has been removed
"""
        assert text_output == expected
