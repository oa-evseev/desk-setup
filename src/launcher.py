from pathlib import Path
import subprocess
import time
from typing import Any

from .backend import (
    arrange_window,
    list_windows,
)
from .models import Config, Window


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


def _window_handle_for_pid(
    windows: list[dict[str, Any]],
    pid: int,
) -> str:

    for window in windows:

        if window.get("pid") == pid:
            return str(
                window.get("handle", "")
            )

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

        windows = list_windows()

        handle = _window_handle_for_pid(
            windows,
            process.pid,
        )

        if handle:
            return handle

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


def _start_process(
    command: list[str],
    cwd: Path | None,
) -> subprocess.Popen:

    return subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


def launch_window(
    window: Window,
    monitor_name: str,
) -> None:

    windows_before = list_windows()

    previous_handles = _window_handles(
        windows_before,
    )

    process = _start_process(
        window.exec,
        window.cwd,
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

        _start_process(
            command.exec,
            (
                command.cwd
                if command.cwd is not None
                else window.cwd
            ),
        )


def launch(config: Config) -> None:

    for (
        monitor_name,
        monitor,
    ) in config.monitors.items():

        for window in monitor.windows:

            launch_window(
                window,
                monitor_name,
            )
