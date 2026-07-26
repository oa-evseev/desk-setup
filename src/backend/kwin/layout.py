from ..types import OutputInfo
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
    outputs: list[OutputInfo],
    monitor_name: str,
) -> OutputInfo:
    enabled_outputs = [
        output
        for output in outputs
        if output.enabled
    ]

    if not enabled_outputs:
        raise RuntimeError(
            "KWin reported no enabled outputs"
        )

    requested_name = str(monitor_name).strip()

    for output in enabled_outputs:
        if output.name == requested_name:
            return output

    requested_name_lower = requested_name.lower()

    for output in enabled_outputs:
        if (
            output.name.lower()
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
            output.name
            for output in enabled_outputs
        )
    )

    raise RuntimeError(
        f"KWin output {monitor_name!r} was not found; "
        f"available outputs: {available}"
    )


def calculate_geometry(
    output: OutputInfo,
    tile: Tile,
) -> dict[str, int]:
    tile_x, tile_y, tile_width, tile_height = (
        geometry_for_tile(tile)
    )

    output_x = round(output.x)
    output_y = round(output.y)
    output_width = round(output.width)
    output_height = round(output.height)

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
    outputs: list[OutputInfo],
    logical_name: str,
) -> OutputInfo:
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
    outputs: list[OutputInfo],
) -> OutputInfo:
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
            output.name,
        ),
    )


def _output_sort_key(
    output: OutputInfo,
) -> tuple[float, float, str]:
    return (
        _output_center_x(output),
        _output_center_y(output),
        output.name,
    )


def _output_left(
    output: OutputInfo,
) -> float:
    return output.x


def _output_right(
    output: OutputInfo,
) -> float:
    return output.x + output.width


def _output_center_x(
    output: OutputInfo,
) -> float:
    return (
        output.x
        + output.width
        / 2.0
    )


def _output_center_y(
    output: OutputInfo,
) -> float:
    return (
        output.y
        + output.height
        / 2.0
    )
