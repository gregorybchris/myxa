import pytest

from myxa.errors import UserError
from myxa.index import Index
from myxa.manager import Manager
from myxa.package import Lock, Package
from myxa.pin import Pin
from myxa.solver import Solver


class TestSolver:
    def test_solve_succeeds_with_no_dependencies(self) -> None:
        index = Index(name="temp")
        target = Package.new("euler", "1.2", [])
        solver = Solver(index=index)
        lock = solver.solve(target)
        assert lock == Lock()

    def test_solve_succeeds_with_middle_dependency_compatible(self) -> None:
        index = Index(name="temp")
        target = Package.new("app", "1.0", [("euler", "2.0"), ("webserver", "0.1")])
        index.add(Package.new("webserver", "0.1", [("euler", "1.0")]))
        index.add(Package.new("webserver", "0.2", [("euler", "2.0")]))
        index.add(Package.new("webserver", "0.3", [("euler", "3.0")]))
        index.add(Package.new("euler", "1.0", []))
        index.add(Package.new("euler", "2.0", []))
        index.add(Package.new("euler", "3.0", []))
        solver = Solver(index=index)
        lock = solver.solve(target)
        assert lock == Lock.new(
            [
                Pin.new("euler", "2.0"),
                Pin.new("webserver", "0.2"),
            ],
            children={
                "app": ["euler", "webserver"],
            },
            sources={
                "euler": "temp",
                "webserver": "temp",
            },
        )

    def test_solve_succeeds_with_highest_minor_versions(self) -> None:
        index = Index(name="temp")
        target = Package.new("app", "1.2", [("euler", "0.1"), ("webserver", "0.2")])
        index.add(Package.new("euler", "0.1", []))
        index.add(Package.new("euler", "0.2", []))
        index.add(Package.new("euler", "0.3", []))
        index.add(Package.new("webserver", "0.2", [("euler", "0.2")]))
        solver = Solver(index=index)
        lock = solver.solve(target)
        assert lock == Lock.new(
            [
                Pin.new("euler", "0.3"),
                Pin.new("webserver", "0.2"),
            ],
            children={
                "app": ["euler", "webserver"],
            },
            sources={
                "webserver": "temp",
                "euler": "temp",
            },
        )

    def test_solve_fails_on_dependency_conflict(self) -> None:
        index = Index(name="temp")
        target = Package.new(
            "app",
            "1.2",
            [("euler", "0.1"), ("webserver", "0.2")],
        )
        index.add(Package.new("euler", "0.1", []))
        index.add(Package.new("euler", "1.0", []))
        index.add(Package.new("webserver", "0.2", [("euler", "1.0")]))
        solver = Solver(index=index)

        with pytest.raises(UserError, match="Failed to solve package dependencies, no valid configuration found"):
            solver.solve(target)

    def test_solve_succeeds_on_cycle_with_current_package(self) -> None:
        index = Index(name="temp")
        target = Package.new("euler", "2.0", [("webserver", "1.0")])
        index.add(Package.new("euler", "1.0", []))
        index.add(Package.new("webserver", "1.0", [("euler", "1.0")]))
        solver = Solver(index=index)
        lock = solver.solve(target)
        assert lock == Lock.new(
            [
                Pin.new("webserver", "1.0"),
            ],
            children={
                "webserver": ["euler"],
                "euler": ["webserver"],
            },
            sources={
                "webserver": "temp",
                "euler": "temp",
            },
        )

    def test_ecosystem(  # noqa: PLR0913
        self,
        manager: Manager,
        solver: Solver,
        primary_index: Index,
        app_package: Package,
        euler_package: Package,
        interlet_package: Package,
        flatty_package: Package,
    ) -> None:
        manager.lock(euler_package, primary_index)
        manager.publish(euler_package, primary_index, interactive=False)
        manager.add(app_package, euler_package.info.name, primary_index, euler_package.info.version)

        manager.lock(flatty_package, primary_index)
        manager.publish(flatty_package, primary_index, interactive=False)
        manager.add(interlet_package, flatty_package.info.name, primary_index, flatty_package.info.version)

        manager.lock(interlet_package, primary_index)
        manager.publish(interlet_package, primary_index, interactive=False)
        manager.add(app_package, interlet_package.info.name, primary_index, interlet_package.info.version)

        lock = solver.solve(app_package)
        assert len(lock) == 3
        for package in [euler_package, flatty_package, interlet_package]:
            lock_package = lock.get(package.info.name)
            assert lock_package.version == package.info.version
