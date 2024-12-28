import pytest
from rich.console import Console

from myxa.errors import UserError
from myxa.models import Index, Package, PackageLock
from myxa.printer import Printer


@pytest.fixture(scope="module", name="printer")
def printer_fixture() -> Printer:
    console = Console()
    return Printer(console=console)


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
        if show_lock:
            with pytest.raises(UserError, match="No lock found for package app"):
                printer.print_package(
                    app_package,
                    show_deps=show_deps,
                    show_lock=show_lock,
                    show_modules=show_modules,
                )

        app_package.lock = PackageLock(deps=app_package.info.deps)
        printer.print_package(
            app_package,
            show_deps=show_deps,
            show_lock=show_lock,
            show_modules=show_modules,
        )

    @pytest.mark.parametrize("show_versions", [True, False])
    def test_print_index(self, printer: Printer, primary_index: Index, show_versions: bool) -> None:
        printer.print_index(
            primary_index,
            show_versions=show_versions,
        )
