from collections.abc import Mapping
from numbers import Real
from typing import Any, cast

from .models import Number, Tile


_PRESETS: dict[
    str,
    tuple[float, float, float, float],
] = {
    "full": (0.0, 0.0, 1.0, 1.0),
    "max": (0.0, 0.0, 1.0, 1.0),
    "left": (0.0, 0.0, 0.5, 1.0),
    "right": (0.5, 0.0, 0.5, 1.0),
    "top": (0.0, 0.0, 1.0, 0.5),
    "bottom": (0.0, 0.5, 1.0, 0.5),
    "top-left": (0.0, 0.0, 0.5, 0.5),
    "top-right": (0.5, 0.0, 0.5, 0.5),
    "bottom-left": (0.0, 0.5, 0.5, 0.5),
    "bottom-right": (0.5, 0.5, 0.5, 0.5),
}

_ALIASES = {
    "fullscreen": "full",
    "maximized": "full",
    "maximised": "full",
    "north": "top",
    "south": "bottom",
    "west": "left",
    "east": "right",
    "north-west": "top-left",
    "northwest": "top-left",
    "nw": "top-left",
    "north-east": "top-right",
    "northeast": "top-right",
    "ne": "top-right",
    "south-west": "bottom-left",
    "southwest": "bottom-left",
    "sw": "bottom-left",
    "south-east": "bottom-right",
    "southeast": "bottom-right",
    "se": "bottom-right",
}

_QUICK_TILE_PRESETS = {
    "left",
    "right",
    "top",
    "bottom",
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
}

_GEOMETRY_FIELDS = (
    "x",
    "y",
    "width",
    "height",
)


class TileError(ValueError):
    """Raised when a tile specification is invalid."""


def normalise_name(value: str) -> str:
    return (
        value
        .strip()
        .lower()
        .replace("_", "-")
        .replace(" ", "-")
    )


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
    )


def _geometry_values(
    tile: Any,
) -> tuple[Any, Any, Any, Any]:
    if isinstance(tile, list):
        if len(tile) != 4:
            raise TileError(
                "Tile geometry must contain "
                "four numbers"
            )

        return tuple(tile)

    if isinstance(tile, Mapping):
        if set(tile) != set(_GEOMETRY_FIELDS):
            raise TileError(
                "Tile geometry must contain x, y, "
                "width and height"
            )

        return tuple(
            tile[field]
            for field in _GEOMETRY_FIELDS
        )

    raise TileError(
        "Tile must be a preset name or "
        "four-part geometry"
    )


def _validate_geometry(
    values: tuple[Any, Any, Any, Any],
) -> tuple[float, float, float, float]:
    if not all(
        _is_number(value)
        for value in values
    ):
        raise TileError(
            "Tile coordinates must be numeric"
        )

    x, y, width, height = (
        float(value)
        for value in values
    )

    if x < 0.0 or y < 0.0:
        raise TileError(
            "Tile origin must be non-negative"
        )

    if width <= 0.0 or height <= 0.0:
        raise TileError(
            "Tile width and height must be positive"
        )

    epsilon = 1e-9

    if (
        x + width > 1.0 + epsilon
        or y + height > 1.0 + epsilon
    ):
        raise TileError(
            "Tile must fit inside the output"
        )

    return x, y, width, height


def validate_tile(value: Any) -> Tile:
    geometry_for_tile(value)

    return cast(Tile, value)


def geometry_for_tile(
    tile: Any,
) -> tuple[float, float, float, float]:
    if isinstance(tile, str):
        name = normalise_name(tile)
        name = _ALIASES.get(name, name)

        try:
            return _PRESETS[name]

        except KeyError as exc:
            supported = ", ".join(
                sorted(_PRESETS)
            )

            raise TileError(
                f"Unknown tile {tile!r}; "
                f"supported presets: {supported}"
            ) from exc

    return _validate_geometry(
        _geometry_values(tile)
    )


def get_quick_tile(
    tile: Tile,
) -> str | None:
    if not isinstance(tile, str):
        return None

    name = normalise_name(tile)
    name = _ALIASES.get(name, name)

    if name in _QUICK_TILE_PRESETS:
        return name

    return None
