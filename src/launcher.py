import subprocess

from .backend.window_finder import wait_for_window
from .backend.window_manager import arrange_window


def run_and_arrange(window, monitor_name) -> None:

    process = subprocess.Popen(
        window.exec,
        cwd=window.cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    window_handle = wait_for_window(process)

    arrange_window(
        window_handle,
        window,
        monitor_name,
    )


def launch(config) -> None:

    for monitor_name, monitor in config.monitors.items():

        for window in monitor.windows:

            run_and_arrange(
                window,
                monitor_name,
            )
