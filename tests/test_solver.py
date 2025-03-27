from myxa.solver import Assignment, Dependency, Index, Package, Solution, Solver, Version


class TestSolver:
    def test_solve_succeeds_with_no_dependencies(self) -> None:
        index = Index()
        target = Package("euler", Version(1, 2))
        solver = Solver(index=index)
        solution = solver.solve(target)
        assert solution == Solution()

    def test_solve_succeeds_with_middle_dependency_compatible(self) -> None:
        index = Index()
        target = Package(
            "app",
            Version(1, 0),
            [
                Dependency("euler", Version(2, 0)),
                Dependency("webserver", Version(0, 1)),
            ],
        )
        index.add(Package("webserver", Version(0, 1), [Dependency("euler", Version(1, 0))]))
        index.add(Package("webserver", Version(0, 2), [Dependency("euler", Version(2, 0))]))
        index.add(Package("webserver", Version(0, 3), [Dependency("euler", Version(3, 0))]))
        index.add(Package("euler", Version(1, 0)))
        index.add(Package("euler", Version(2, 0)))
        index.add(Package("euler", Version(3, 0)))
        solver = Solver(index=index)
        solution = solver.solve(target)
        assert solution == Solution.new([Assignment("euler", Version(2, 0)), Assignment("webserver", Version(0, 2))])

    def test_solve_succeeds_with_highest_minor_versions(self) -> None:
        index = Index()
        target = Package(
            "app",
            Version(1, 2),
            [
                Dependency("euler", Version(0, 1)),
                Dependency("webserver", Version(0, 2)),
            ],
        )
        index.add(Package("euler", Version(0, 1)))
        index.add(Package("euler", Version(0, 2)))
        index.add(Package("euler", Version(0, 3)))
        index.add(Package("webserver", Version(0, 2), [Dependency("euler", Version(0, 2))]))
        solver = Solver(index=index)
        solution = solver.solve(target)
        assert solution == Solution.new([Assignment("euler", Version(0, 3)), Assignment("webserver", Version(0, 2))])

    def test_solve_fails_on_dependency_conflict(self) -> None:
        index = Index()
        target = Package(
            "app",
            Version(1, 2),
            [
                Dependency("euler", Version(0, 1)),
                Dependency("webserver", Version(0, 2)),
            ],
        )
        index.add(Package("euler", Version(0, 1)))
        index.add(Package("euler", Version(1, 0)))
        index.add(Package("webserver", Version(0, 2), [Dependency("euler", Version(1, 0))]))
        solver = Solver(index=index)
        solution = solver.solve(target)
        assert solution is None

    def test_solve_succeeds_on_cycle_with_current_package(self) -> None:
        index = Index()
        target = Package("euler", Version(2, 0), [Dependency("webserver", Version(1, 0))])
        index.add(Package("euler", Version(1, 0)))
        index.add(Package("webserver", Version(1, 0), [Dependency("euler", Version(1, 0))]))
        solver = Solver(index=index)
        solution = solver.solve(target)
        assert solution == Solution.new([Assignment("webserver", Version(1, 0))])


class TestSolution:
    def test_package_compatible_with_empty_solution(self) -> None:
        package = Package("euler", Version(1, 2))
        solution = Solution()
        assert solution.is_compatible_with(package)

    def test_package_compatible_with_solution_containing_self(self) -> None:
        package = Package("euler", Version(1, 2))
        solution = Solution()
        assignment = Assignment("euler", Version(1, 2))
        solution.add(assignment)
        assert solution.is_compatible_with(package)

    def test_package_incompatible_with_solution(self) -> None:
        package = Package("euler", Version(1, 2))
        solution = Solution()
        assignment = Assignment("euler", Version(1, 1))
        solution.add(assignment)
        assert not solution.is_compatible_with(package)


class TestDependency:
    def test_higher_minor_satisfies_lower_minor(self) -> None:
        version = Version(1, 2)
        dependency = Dependency("euler", Version(1, 1))
        assert dependency.is_satisfied_by(version)

    def test_lower_minor_does_not_satisfy_higher_minor(self) -> None:
        version = Version(1, 1)
        dependency = Dependency("euler", Version(1, 2))
        assert not dependency.is_satisfied_by(version)

    def test_higher_major_does_not_satisfy_lower_major(self) -> None:
        version = Version(2, 0)
        dependency = Dependency("euler", Version(1, 2))
        assert not dependency.is_satisfied_by(version)

    def test_lower_major_does_not_satisfy_higher_major(self) -> None:
        version = Version(0, 1)
        dependency = Dependency("euler", Version(1, 0))
        assert not dependency.is_satisfied_by(version)

    def test_same_version_satisfies_dependency(self) -> None:
        version = Version(1, 2)
        dependency = Dependency("euler", Version(1, 2))
        assert dependency.is_satisfied_by(version)
