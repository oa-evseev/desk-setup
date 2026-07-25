from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Window:
    exec: list[str]
    cwd: Path | None
    tile: str


@dataclass(slots=True)
class Monitor:
    windows: list[Window]


@dataclass(slots=True)
class Config:
    version: int
    monitors: dict[str, Monitor]
