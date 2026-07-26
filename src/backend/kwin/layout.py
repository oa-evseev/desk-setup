from collections.abc import Mapping
from numbers import Real
from typing import Any

from ...models import Tile
from ...tiles import (
    geometry_for_tile,
    get_quick_tile,
    normalise_name,
)


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
    tile: Tile,
) -> dict[str, int]:
    tile_x, tile_y, tile_width, tile_height = (
        geometry_for_tile(tile)
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


def _normalise_monitor_name(
    monitor_name: str,
) -> str | None:
    name = normalise_name(monitor_name)

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


def _as_int(
    output: Mapping[str, Any],
    key: str,
) -> int:
    return round(
        float(
            _output_number(output, key)
        )
    )
