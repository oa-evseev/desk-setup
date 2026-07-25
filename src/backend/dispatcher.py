import os
from typing import Any

from . import kwin


def find_window(
    pid: int,
) -> str:

    wm = detect_window_manager()

    return wm.find_window(pid)


def list_windows() -> list[dict[str, Any]]:

    wm = detect_window_manager()

    return wm.list_windows()


def arrange_window(
    window_handle: str,
    window: Any,
    monitor_name: str,
) -> None:

    wm = detect_window_manager()

    wm.arrange_window(
        window_handle,
        window,
        monitor_name,
    )


def detect_window_manager():

    session = os.environ.get(
        "XDG_CURRENT_DESKTOP",
        "",
    ).lower()

    if "kde" in session:
        return kwin

    raise NotImplementedError(
        "Unsupported desktop environment: "
        f"{session!r}"
    )
