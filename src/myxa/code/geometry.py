import math
from enum import StrEnum, auto


def area(radius: float) -> float:
    return math.pi * radius**2


class PizzaType(StrEnum):
    Chicago = auto()
    Detroit = auto()
    NewYork = auto()
