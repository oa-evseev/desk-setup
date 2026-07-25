from pathlib import Path

import yaml

from .models import Config, Monitor, Window


SUPPORTED_VERSION = 1


def load_config(path: Path) -> Config:

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("Configuration must be a mapping.")

    version = data.get("version")

    if version != SUPPORTED_VERSION:
        raise ValueError(
            f"Unsupported configuration version: {version}"
        )

    monitors: dict[str, Monitor] = {}

    for monitor_name, monitor_data in data["monitors"].items():

        windows: list[Window] = []

        for window in monitor_data.get("windows", []):

            cwd = window.get("cwd")

            windows.append(
                Window(
                    exec=list(window["exec"]),
                    cwd=Path(cwd).expanduser() if cwd else None,
                    tile=window["tile"],
                )
            )

        monitors[monitor_name] = Monitor(
            windows=windows,
        )

    return Config(
        version=version,
        monitors=monitors,
    )
