from myxa.pin import Pin


class TestPin:
    def test_to_str(self) -> None:
        pin = Pin.new("euler", "1.2")
        assert str(pin) == "euler==1.2"
