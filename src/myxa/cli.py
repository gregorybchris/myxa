import logging

from rich.console import Console
from rich.logging import RichHandler
from typer import Typer

from myxa.main import Manager, main

logger = logging.getLogger(__name__)


app = Typer(pretty_exceptions_enable=False)
console = Console()


def set_logger_config(info: bool, debug: bool) -> None:
    handlers = [RichHandler(rich_tracebacks=True)]
    log_format = "%(message)s"

    if info:
        logging.basicConfig(level=logging.INFO, handlers=handlers, format=log_format)
    if debug:
        logging.basicConfig(level=logging.DEBUG, handlers=handlers, format=log_format)


@app.command()
def go(
    info: bool = False,
    debug: bool = False,
) -> None:
    set_logger_config(info, debug)
    logger.info("Go!")


@app.command()
def run(
    info: bool = False,
    debug: bool = False,
) -> None:
    set_logger_config(info, debug)
    logger.info("Running myxa")

    manager = Manager(console=console)
    main(manager)
