from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WindowInfo:
    handle: str
    pid: int


@dataclass(frozen=True, slots=True)
class OutputInfo:
    name: str
    x: float
    y: float
    width: float
    height: float
    enabled: bool
