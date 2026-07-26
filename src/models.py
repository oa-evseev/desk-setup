from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Command:
    exec: list[str]
    cwd: Path | None


@dataclass(slots=True)
class Window:
    exec: list[str]
    cwd: Path | None
    tile: str
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
