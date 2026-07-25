from typing import Any

from .client import (
    activate_window,
    find_window,
    list_outputs,
    list_windows,
    move_resize_window,
    quick_tile_window,
)
from .layout import (
    calculate_geometry,
    find_output,
    get_quick_tile,
)


def arrange_window(
    window_handle: str,
    window: Any,
    monitor_name: str,
) -> None:

    outputs = list_outputs()

    output = find_output(
        outputs,
        monitor_name,
    )

    geometry = calculate_geometry(
        output,
        window.tile,
    )

    # First place the window explicitly. This ensures
    # that it is on the intended output and provides a
    # usable fallback if native Quick Tile fails.
    move_resize_window(
        window_handle,
        **geometry,
    )

    quick_tile = get_quick_tile(
        window.tile,
    )

    if quick_tile is not None:

        quick_tile_window(
            window_handle,
            quick_tile,
        )

    activate_window(
        window_handle,
    )


__all__ = [
    "activate_window",
    "arrange_window",
    "calculate_geometry",
    "find_output",
    "find_window",
    "get_quick_tile",
    "list_outputs",
    "list_windows",
    "move_resize_window",
    "quick_tile_window",
]
