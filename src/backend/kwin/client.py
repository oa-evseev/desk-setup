from collections.abc import Mapping
import math
from numbers import Real
from typing import Any

from ..types import OutputInfo, WindowInfo
from .transport import call


def _mapping(
    value: Any,
    path: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(
            f"KWin returned invalid {path}: "
            "expected a mapping"
        )

    return value


def _string(
    data: Mapping[str, Any],
    field: str,
    path: str,
) -> str:
    value = data.get(field)

    if (
        not isinstance(value, str)
        or not value
    ):
        raise RuntimeError(
            f"KWin returned invalid {path}.{field}: "
            "expected a non-empty string"
        )

    return value


def _integer(
    data: Mapping[str, Any],
    field: str,
    path: str,
) -> int:
    value = data.get(field)

    if (
        not isinstance(value, int)
        or isinstance(value, bool)
    ):
        raise RuntimeError(
            f"KWin returned invalid {path}.{field}: "
            "expected an integer"
        )

    return value


def _number(
    data: Mapping[str, Any],
    field: str,
    path: str,
) -> float:
    value = data.get(field)

    if (
        not isinstance(value, Real)
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise RuntimeError(
            f"KWin returned invalid {path}.{field}: "
            "expected a finite number"
        )

    return float(value)


def _window_info(
    value: Any,
    index: int,
) -> WindowInfo:
    path = f"window list item {index}"
    data = _mapping(value, path)

    return WindowInfo(
        handle=_string(
            data,
            "handle",
            path,
        ),
        pid=_integer(
            data,
            "pid",
            path,
        ),
    )


def _output_info(
    value: Any,
    index: int,
) -> OutputInfo:
    path = f"output list item {index}"
    data = _mapping(value, path)

    width = _number(
        data,
        "width",
        path,
    )
    height = _number(
        data,
        "height",
        path,
    )

    if width <= 0 or height <= 0:
        raise RuntimeError(
            f"KWin returned invalid {path}: "
            "width and height must be positive"
        )

    enabled = data.get("enabled", True)

    if not isinstance(enabled, bool):
        raise RuntimeError(
            f"KWin returned invalid {path}.enabled: "
            "expected a boolean"
        )

    return OutputInfo(
        name=_string(
            data,
            "name",
            path,
        ),
        x=_number(data, "x", path),
        y=_number(data, "y", path),
        width=width,
        height=height,
        enabled=enabled,
    )


def list_windows() -> list[WindowInfo]:
    result = call(
        "listWindows",
    )

    if not isinstance(result, list):
        raise RuntimeError(
            "KWin returned an invalid window list"
        )

    return [
        _window_info(window, index)
        for index, window in enumerate(result)
    ]


def list_outputs() -> list[OutputInfo]:
    result = call(
        "listOutputs",
    )

    if not isinstance(result, list):
        raise RuntimeError(
            "KWin returned an invalid output list"
        )

    return [
        _output_info(output, index)
        for index, output in enumerate(result)
    ]


def move_resize_window(
    window_handle: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
) -> bool:
    return bool(
        call(
            "moveResizeWindow",
            handle=str(window_handle),
            x=int(x),
            y=int(y),
            width=int(width),
            height=int(height),
        )
    )


def quick_tile_window(
    window_handle: str,
    tile: str,
) -> bool:
    return bool(
        call(
            "quickTileWindow",
            handle=str(window_handle),
            tile=str(tile),
        )
    )


def activate_window(
    window_handle: str,
) -> bool:
    return bool(
        call(
            "activateWindow",
            handle=str(window_handle),
        )
    )


__all__ = [
    "activate_window",
    "list_outputs",
    "list_windows",
    "move_resize_window",
    "quick_tile_window",
]
