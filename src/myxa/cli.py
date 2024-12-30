import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Generator, Optional

import typer
from rich.logging import RichHandler
from typer import Typer

from myxa.errors import UserError
from myxa.manager import Manager
from myxa.models import Index, Version

logger = logging.getLogger(__name__)

DEFAULT_PACKAGE_FILEPATH = Path("package.json")

app = Typer(pretty_exceptions_enable=False)


def set_logger_config(info: bool, debug: bool) -> None:
    handlers = [RichHandler(rich_tracebacks=True)]
    log_format = "%(message)s"

    if info:
        logging.basicConfig(level=logging.INFO, handlers=handlers, format=log_format)
    if debug:
        logging.basicConfig(level=logging.DEBUG, handlers=handlers, format=log_format)


def load_index_path() -> Path:
    index_filepath_str = os.getenv("MYXA_INDEX")
    if index_filepath_str is None:
        msg = "MYXA_INDEX environment variable not set"
        raise UserError(msg)
    return Path(index_filepath_str)


def load_index(manager: Manager) -> Index:
    index_filepath = load_index_path()
    if not index_filepath.exists():
        index = Index(name="primary")
        save_index(manager, index)
    return manager.load_index(index_filepath)


def save_index(manager: Manager, index: Index) -> None:
    index_filepath = load_index_path()
    manager.save_index(index, index_filepath)


@contextmanager
def error_handler(manager: Manager, debug: bool = False) -> Generator[None, None, None]:
    try:
        yield
    except UserError as exc:
        manager.printer.print_error(str(exc))
        if debug:
            raise exc


@app.command(help="Initialize a new package")
def init(name: str, description: str, info: bool = False, debug: bool = False) -> None:
    set_logger_config(info, debug)
    manager = Manager()
    with error_handler(manager, debug=debug):
        manager.init(name, description, DEFAULT_PACKAGE_FILEPATH)


@app.command(help="Print information about the package")
def info(
    show_deps: Annotated[bool, typer.Option("--show-deps/--no-deps")] = True,
    show_lock: Annotated[bool, typer.Option("--show-lock/--no-lock")] = True,
    show_modules: Annotated[bool, typer.Option("--show-modules/--no-modules")] = True,
    info: bool = False,
    debug: bool = False,
) -> None:
    set_logger_config(info, debug)
    manager = Manager()
    with error_handler(manager, debug=debug):
        package = manager.load_package(DEFAULT_PACKAGE_FILEPATH)
        manager.printer.print_package(
            package,
            show_deps=show_deps,
            show_lock=show_lock,
            show_modules=show_modules,
        )


# show alias for the info command
app.command(name="show")(info)


@app.command(help="Lock the package dependencies")
def lock(info: bool = False, debug: bool = False) -> None:
    set_logger_config(info, debug)
    manager = Manager()
    with error_handler(manager, debug=debug):
        package = manager.load_package(DEFAULT_PACKAGE_FILEPATH)
        index = load_index(manager)
        manager.lock(package, index)
        manager.save_package(package, DEFAULT_PACKAGE_FILEPATH)


@app.command(help="Unlock the package dependencies")
def unlock(info: bool = False, debug: bool = False) -> None:
    set_logger_config(info, debug)
    manager = Manager()
    with error_handler(manager, debug=debug):
        package = manager.load_package(DEFAULT_PACKAGE_FILEPATH)
        manager.unlock(package)
        manager.save_package(package, DEFAULT_PACKAGE_FILEPATH)


@app.command(help="Add a dependency to the package")
def add(dep_name: str, version: Optional[str] = None, info: bool = False, debug: bool = False) -> None:
    set_logger_config(info, debug)
    manager = Manager()
    with error_handler(manager, debug=debug):
        package = manager.load_package(DEFAULT_PACKAGE_FILEPATH)
        index = load_index(manager)
        version_obj = Version.from_str(version) if version else None
        manager.add(package, dep_name, index, version=version_obj)
        manager.save_package(package, DEFAULT_PACKAGE_FILEPATH)


@app.command(help="Remove a dependency from the package")
def remove(dep_name: str, info: bool = False, debug: bool = False) -> None:
    set_logger_config(info, debug)
    manager = Manager()
    with error_handler(manager, debug=debug):
        package = manager.load_package(DEFAULT_PACKAGE_FILEPATH)
        manager.remove(package, dep_name)
        manager.save_package(package, DEFAULT_PACKAGE_FILEPATH)


@app.command(help="Publish the current package to the index")
def publish(info: bool = False, debug: bool = False) -> None:
    set_logger_config(info, debug)
    manager = Manager()
    with error_handler(manager, debug=debug):
        package = manager.load_package(DEFAULT_PACKAGE_FILEPATH)
        index = load_index(manager)
        manager.publish(package, index)
        save_index(manager, index)


@app.command(help="Check if there are breaking changes")
def check(info: bool = False, debug: bool = False) -> None:
    set_logger_config(info, debug)
    manager = Manager()
    with error_handler(manager, debug=debug):
        package = manager.load_package(DEFAULT_PACKAGE_FILEPATH)
        index = load_index(manager)
        manager.check(package, index)
        manager.save_package(package, DEFAULT_PACKAGE_FILEPATH)


@app.command(help="Yank the current package from the index")
def yank(version: str, info: bool = False, debug: bool = False) -> None:
    version_obj = Version.from_str(version)
    set_logger_config(info, debug)
    manager = Manager()
    with error_handler(manager, debug=debug):
        package = manager.load_package(DEFAULT_PACKAGE_FILEPATH)
        index = load_index(manager)
        manager.yank(package, version_obj, index)
        save_index(manager, index)


@app.command(help="Update all dependencies to the latest compatible version")
def update(info: bool = False, debug: bool = False) -> None:
    set_logger_config(info, debug)
    manager = Manager()
    with error_handler(manager, debug=debug):
        package = manager.load_package(DEFAULT_PACKAGE_FILEPATH)
        index = load_index(manager)
        manager.update(package, index)
        manager.save_package(package, DEFAULT_PACKAGE_FILEPATH)


@app.command(help="List all packages in the index")
def index(
    show_versions: Annotated[bool, typer.Option("--show-versions/--no-versions")] = True,
    info: bool = False,
    debug: bool = False,
) -> None:
    set_logger_config(info, debug)
    manager = Manager()
    with error_handler(manager, debug=debug):
        index = load_index(manager)
        manager.printer.print_index(index, show_versions=show_versions)


@app.command(help="Set the version of the package")
def version(version: str, info: bool = False, debug: bool = False) -> None:
    set_logger_config(info, debug)
    manager = Manager()
    with error_handler(manager, debug=debug):
        package = manager.load_package(DEFAULT_PACKAGE_FILEPATH)
        version_obj = Version.from_str(version)
        manager.set_version(package, version_obj)
        manager.save_package(package, DEFAULT_PACKAGE_FILEPATH)
