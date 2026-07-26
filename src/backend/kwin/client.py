from typing import Any

from .transport import call


def list_windows() -> list[dict[str, Any]]:
    result = call(
        "listWindows",
    )

    if not isinstance(result, list):
        raise RuntimeError(
            "KWin returned an invalid window list"
        )

    return result


def list_outputs() -> list[dict[str, Any]]:
    result = call(
        "listOutputs",
    )

    if not isinstance(result, list):
        raise RuntimeError(
            "KWin returned an invalid output list"
        )

    return result


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
