from dataclasses import dataclass, field
from pathlib import Path


Number = int | float
Tile = (
    str
    | list[Number]
    | dict[str, Number]
)


@dataclass(slots=True)
class Command:
    exec: list[str]
    cwd: Path | None


@dataclass(slots=True)
class Window:
    exec: list[str]
    cwd: Path | None
    tile: Tile
    after: list[Command] = field(
        default_factory=list,
    )


@dataclass(slots=True)
class Monitor:
    windows: list[Window]


@dataclass(slots=True)
class Config:
    version: int
    monitors: dict[str, Monitor]
    description: str | None = None
