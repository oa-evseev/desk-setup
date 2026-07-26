import subprocess
import time
from typing import Any

from .backend import (
    arrange_window,
    find_window,
    list_windows,
)


_WINDOW_TIMEOUT = 15.0
_POLL_INTERVAL = 0.1


def _window_handles(
    windows: list[dict[str, Any]],
) -> set[str]:

    return {
        str(window["handle"])
        for window in windows
        if window.get("handle")
    }


def _new_window_handle(
    windows: list[dict[str, Any]],
    previous_handles: set[str],
) -> str:

    for window in reversed(windows):

        handle = str(
            window.get(
                "handle",
                "",
            )
        )

        if (
            handle
            and handle not in previous_handles
        ):
            return handle

    return ""


def _wait_for_window(
    process: subprocess.Popen,
    previous_handles: set[str],
) -> str:

    deadline = (
        time.monotonic()
        + _WINDOW_TIMEOUT
    )

    while time.monotonic() < deadline:

        # Prefer the PID when the application creates
        # a window in the newly launched process.
        handle = find_window(
            process.pid,
        )

        if handle:
            return handle

        # Applications such as Firefox may forward
        # the request to an already running process.
        # In that case, detect the newly created KWin
        # window by its handle instead.
        windows = list_windows()

        handle = _new_window_handle(
            windows,
            previous_handles,
        )

        if handle:
            return handle

        time.sleep(
            _POLL_INTERVAL,
        )

    current_windows = list_windows()

    current_handles = _window_handles(
        current_windows,
    )

    new_handles = sorted(
        current_handles
        - previous_handles
    )

    raise RuntimeError(
        "No KWin window appeared within "
        f"{_WINDOW_TIMEOUT:.1f} seconds "
        f"after launching PID {process.pid}; "
        f"new handles observed: {new_handles}"
    )


def launch_window(
    window,
    monitor_name: str,
) -> None:

    windows_before = list_windows()

    previous_handles = _window_handles(
        windows_before,
    )

    process = subprocess.Popen(
        window.exec,
        cwd=window.cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    window_handle = _wait_for_window(
        process,
        previous_handles,
    )

    arrange_window(
        window_handle,
        window,
        monitor_name,
    )

    for command in window.after:

        subprocess.Popen(
            command.exec,
            cwd=(
                command.cwd
                if command.cwd is not None
                else window.cwd
            ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )


def launch(config) -> None:

    for (
        monitor_name,
        monitor,
    ) in config.monitors.items():

        for window in monitor.windows:

            launch_window(
                window,
                monitor_name,
            )
