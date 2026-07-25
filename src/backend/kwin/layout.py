from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any


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


_ALIASES: dict[str, str] = {
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


_MONITOR_ALIASES: dict[str, str] = {
    "left": "left",
    "leftmost": "left",
    "west": "left",
    "first": "left",
    "center": "center",
    "centre": "center",
    "middle": "center",
    "right": "right",
    "rightmost": "right",
    "east": "right",
    "last": "right",
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

def find_output(
    outputs: list[dict[str, Any]],
    monitor_name: str,
) -> dict[str, Any]:
    enabled_outputs = [
        output
        for output in outputs
        if output.get("enabled", True) is not False
    ]

    if not enabled_outputs:
        raise RuntimeError(
            "KWin reported no enabled outputs"
        )

    requested_name = str(monitor_name).strip()

    for output in enabled_outputs:
        if str(output.get("name", "")) == requested_name:
            return output

    requested_name_lower = requested_name.lower()

    for output in enabled_outputs:
        if (
            str(output.get("name", "")).lower()
            == requested_name_lower
        ):
            return output

    logical_name = _normalise_monitor_name(
        requested_name
    )

    if logical_name is not None:
        return _find_logical_output(
            enabled_outputs,
            logical_name,
        )

    available = ", ".join(
        sorted(
            str(output.get("name", ""))
            for output in enabled_outputs
        )
    )

    raise RuntimeError(
        f"KWin output {monitor_name!r} was not found; "
        f"available outputs: {available}"
    )


def calculate_geometry(
    output: Mapping[str, Any],
    tile: Any,
) -> dict[str, int]:
    tile_x, tile_y, tile_width, tile_height = (
        _normalise_tile(tile)
    )

    output_x = _as_int(output, "x")
    output_y = _as_int(output, "y")
    output_width = _as_int(output, "width")
    output_height = _as_int(output, "height")

    left = (
        output_x
        + round(output_width * tile_x)
    )

    top = (
        output_y
        + round(output_height * tile_y)
    )

    right = (
        output_x
        + round(
            output_width
            * (tile_x + tile_width)
        )
    )

    bottom = (
        output_y
        + round(
            output_height
            * (tile_y + tile_height)
        )
    )

    return {
        "x": left,
        "y": top,
        "width": max(1, right - left),
        "height": max(1, bottom - top),
    }


def get_quick_tile(
    tile: Any,
) -> str | None:
    """
    Return a native KWin Quick Tile name when the
    configured tile is a compatible string preset.

    Explicit mappings, sequences and tile objects
    remain manually positioned geometries.
    """
    if not isinstance(tile, str):
        return None

    name = (
        tile
        .strip()
        .lower()
        .replace("_", "-")
        .replace(" ", "-")
    )

    name = _ALIASES.get(
        name,
        name,
    )

    if name in _QUICK_TILE_PRESETS:
        return name

    return None


def _normalise_monitor_name(
    monitor_name: str,
) -> str | None:
    name = (
        monitor_name
        .strip()
        .lower()
        .replace("_", "-")
        .replace(" ", "-")
    )

    return _MONITOR_ALIASES.get(name)


def _find_logical_output(
    outputs: list[dict[str, Any]],
    logical_name: str,
) -> dict[str, Any]:
    ordered = sorted(
        outputs,
        key=_output_sort_key,
    )

    if logical_name == "left":
        return ordered[0]

    if logical_name == "right":
        return ordered[-1]

    if logical_name == "center":
        return _find_center_output(ordered)

    raise RuntimeError(
        f"Unknown logical monitor name: "
        f"{logical_name!r}"
    )


def _find_center_output(
    outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(outputs) == 1:
        return outputs[0]

    desktop_left = min(
        _output_left(output)
        for output in outputs
    )

    desktop_right = max(
        _output_right(output)
        for output in outputs
    )

    desktop_center = (
        desktop_left + desktop_right
    ) / 2.0

    return min(
        outputs,
        key=lambda output: (
            abs(
                _output_center_x(output)
                - desktop_center
            ),
            _output_center_x(output),
            _output_center_y(output),
            str(output.get("name", "")),
        ),
    )


def _output_sort_key(
    output: Mapping[str, Any],
) -> tuple[float, float, str]:
    return (
        _output_center_x(output),
        _output_center_y(output),
        str(output.get("name", "")),
    )


def _output_left(
    output: Mapping[str, Any],
) -> float:
    return float(
        _output_number(output, "x")
    )


def _output_right(
    output: Mapping[str, Any],
) -> float:
    return (
        float(_output_number(output, "x"))
        + float(_output_number(output, "width"))
    )


def _output_center_x(
    output: Mapping[str, Any],
) -> float:
    return (
        float(_output_number(output, "x"))
        + float(_output_number(output, "width"))
        / 2.0
    )


def _output_center_y(
    output: Mapping[str, Any],
) -> float:
    return (
        float(_output_number(output, "y"))
        + float(_output_number(output, "height"))
        / 2.0
    )


def _output_number(
    output: Mapping[str, Any],
    key: str,
) -> Real:
    try:
        value = output[key]

    except KeyError as exc:
        raise RuntimeError(
            f"KWin output is missing {key!r}: "
            f"{dict(output)!r}"
        ) from exc

    if not isinstance(value, Real):
        raise RuntimeError(
            f"KWin output field {key!r} "
            f"is not numeric: {value!r}"
        )

    return value


def _normalise_tile(
    tile: Any,
) -> tuple[float, float, float, float]:
    if tile is None:
        return _PRESETS["full"]

    if isinstance(tile, str):
        name = (
            tile
            .strip()
            .lower()
            .replace("_", "-")
            .replace(" ", "-")
        )

        name = _ALIASES.get(name, name)

        try:
            return _PRESETS[name]

        except KeyError as exc:
            supported = ", ".join(
                sorted(_PRESETS)
            )

            raise ValueError(
                f"Unknown tile {tile!r}; "
                f"supported presets: {supported}"
            ) from exc

    if isinstance(tile, Mapping):
        values = (
            tile.get("x"),
            tile.get("y"),
            tile.get("width"),
            tile.get("height"),
        )

        return _validate_tile(
            values,
            tile,
        )

    if (
        isinstance(tile, Sequence)
        and not isinstance(
            tile,
            (str, bytes, bytearray),
        )
        and len(tile) == 4
    ):
        return _validate_tile(
            tuple(tile),
            tile,
        )

    attributes = tuple(
        getattr(
            tile,
            name,
            None,
        )
        for name in (
            "x",
            "y",
            "width",
            "height",
        )
    )

    if all(
        value is not None
        for value in attributes
    ):
        return _validate_tile(
            attributes,
            tile,
        )

    raise TypeError(
        "tile must be a preset name, "
        "a four-item sequence, a mapping, "
        "or an object with x, y, width "
        "and height attributes"
    )


def _validate_tile(
    values: tuple[Any, Any, Any, Any],
    original: Any,
) -> tuple[float, float, float, float]:
    if not all(
        isinstance(value, Real)
        for value in values
    ):
        raise TypeError(
            "Tile coordinates must be numeric: "
            f"{original!r}"
        )

    x, y, width, height = (
        float(value)
        for value in values
    )

    if x < 0.0 or y < 0.0:
        raise ValueError(
            "Tile origin must be non-negative: "
            f"{original!r}"
        )

    if width <= 0.0 or height <= 0.0:
        raise ValueError(
            "Tile width and height must be positive: "
            f"{original!r}"
        )

    epsilon = 1e-9

    if (
        x + width > 1.0 + epsilon
        or y + height > 1.0 + epsilon
    ):
        raise ValueError(
            "Tile must fit inside the output: "
            f"{original!r}"
        )

    return x, y, width, height


def _as_int(
    output: Mapping[str, Any],
    key: str,
) -> int:
    return round(
        float(
            _output_number(output, key)
        )
    )
