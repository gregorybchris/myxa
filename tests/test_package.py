from myxa.package import Lock, Package
from myxa.pin import Pin


class TestPackage:
    def test_lock_to_str(self) -> None:
        lock = Lock()
        assert str(lock) == "<empty>"
        lock.add(Pin.new("euler", "1.2"))
        assert str(lock) == "<euler==1.2>"
        lock.add(Pin.new("webserver", "0.1"))
        assert str(lock) == "<euler==1.2, webserver==0.1>"

    def test_package_compatible_with_empty_lock(self) -> None:
        package = Package.new("euler", "1.2", [])
        lock = Lock()
        assert lock.is_compatible_with(package)

    def test_package_compatible_with_lock_containing_self(self) -> None:
        package = Package.new("euler", "1.2", [])
        lock = Lock()
        pin = Pin.new("euler", "1.2")
        lock.add(pin)
        assert lock.is_compatible_with(package)

    def test_package_incompatible_with_lock(self) -> None:
        package = Package.new("euler", "1.2", [])
        lock = Lock()
        pin = Pin.new("euler", "1.1")
        lock.add(pin)
        assert not lock.is_compatible_with(package)
