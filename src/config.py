from collections.abc import Mapping
from numbers import Real
from pathlib import Path
from typing import Any

import yaml

from .models import (
    Command,
    Config,
    Monitor,
    Tile,
    Window,
)


SUPPORTED_VERSION = 1


class ConfigError(ValueError):
    """Raised when a configuration cannot be loaded."""


def _mapping(
    value: Any,
    path: str,
) -> Mapping[Any, Any]:
    if not isinstance(value, Mapping):
        raise ConfigError(
            f"{path} must be a mapping"
        )

    return value


def _list(
    value: Any,
    path: str,
) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigError(
            f"{path} must be a list"
        )

    return value


def _check_fields(
    data: Mapping[Any, Any],
    allowed: set[str],
    path: str,
) -> None:
    for field in data:
        if field not in allowed:
            raise ConfigError(
                f"{path}.{field} is unknown"
            )


def _required(
    data: Mapping[Any, Any],
    field: str,
    path: str,
) -> Any:
    if field not in data:
        raise ConfigError(
            f"{path}.{field} is required"
        )

    return data[field]


def _parse_exec(
    value: Any,
    path: str,
) -> list[str]:
    arguments = _list(value, path)

    if (
        not arguments
        or not all(
            isinstance(argument, str)
            for argument in arguments
        )
        or not arguments[0]
    ):
        raise ConfigError(
            f"{path} must be a non-empty "
            "list of strings"
        )

    return list(arguments)


def _parse_cwd(
    value: Any,
    path: str,
) -> Path | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise ConfigError(
            f"{path} must be a path string"
        )

    if not value:
        raise ConfigError(
            f"{path} must not be empty"
        )

    return Path(value).expanduser()


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
    )


def _parse_tile(
    value: Any,
    path: str,
) -> Tile:
    if isinstance(value, str):
        if not value.strip():
            raise ConfigError(
                f"{path} must not be empty"
            )

        return value

    if isinstance(value, list):
        if (
            len(value) != 4
            or not all(
                _is_number(number)
                for number in value
            )
        ):
            raise ConfigError(
                f"{path} must contain four numbers"
            )

        return list(value)

    if isinstance(value, Mapping):
        fields = {
            "x",
            "y",
            "width",
            "height",
        }

        _check_fields(value, fields, path)

        if set(value) != fields:
            raise ConfigError(
                f"{path} must contain x, y, "
                "width and height"
            )

        if not all(
            _is_number(value[field])
            for field in fields
        ):
            raise ConfigError(
                f"{path} values must be numeric"
            )

        return {
            field: value[field]
            for field in (
                "x",
                "y",
                "width",
                "height",
            )
        }

    raise ConfigError(
        f"{path} must be a preset name "
        "or four-part geometry"
    )


def _parse_command(
    value: Any,
    path: str,
) -> Command:
    data = _mapping(value, path)
    _check_fields(
        data,
        {"exec", "cwd"},
        path,
    )

    return Command(
        exec=_parse_exec(
            _required(data, "exec", path),
            f"{path}.exec",
        ),
        cwd=_parse_cwd(
            data.get("cwd"),
            f"{path}.cwd",
        ),
    )


def _parse_window(
    value: Any,
    path: str,
) -> Window:
    data = _mapping(value, path)
    _check_fields(
        data,
        {
            "exec",
            "cwd",
            "tile",
            "after",
        },
        path,
    )

    after_data = _list(
        data.get("after", []),
        f"{path}.after",
    )

    return Window(
        exec=_parse_exec(
            _required(data, "exec", path),
            f"{path}.exec",
        ),
        cwd=_parse_cwd(
            data.get("cwd"),
            f"{path}.cwd",
        ),
        tile=_parse_tile(
            _required(data, "tile", path),
            f"{path}.tile",
        ),
        after=[
            _parse_command(
                command,
                f"{path}.after[{index}]",
            )
            for index, command in enumerate(
                after_data
            )
        ],
    )


def _parse_monitor(
    value: Any,
    path: str,
) -> Monitor:
    data = _mapping(value, path)
    _check_fields(
        data,
        {"windows"},
        path,
    )

    windows_data = _list(
        data.get("windows", []),
        f"{path}.windows",
    )

    return Monitor(
        windows=[
            _parse_window(
                window,
                f"{path}.windows[{index}]",
            )
            for index, window in enumerate(
                windows_data
            )
        ]
    )


def _parse_config(value: Any) -> Config:
    data = _mapping(
        value,
        "configuration",
    )
    _check_fields(
        data,
        {"version", "monitors"},
        "configuration",
    )

    version = data.get("version")

    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or version != SUPPORTED_VERSION
    ):
        raise ConfigError(
            "Unsupported configuration "
            f"version: {version}"
        )

    monitors_data = _mapping(
        _required(
            data,
            "monitors",
            "configuration",
        ),
        "monitors",
    )

    monitors: dict[str, Monitor] = {}

    for name, monitor in monitors_data.items():
        if (
            not isinstance(name, str)
            or not name.strip()
        ):
            raise ConfigError(
                "monitor names must be "
                "non-empty strings"
            )

        monitors[name] = _parse_monitor(
            monitor,
            f"monitors.{name}",
        )

    return Config(
        version=version,
        monitors=monitors,
    )


def load_config(path: Path) -> Config:
    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = yaml.safe_load(file)

    except OSError as exc:
        raise ConfigError(
            "Could not read configuration "
            f"{path}: {exc}"
        ) from exc

    except yaml.YAMLError as exc:
        raise ConfigError(
            f"Invalid YAML in {path}: {exc}"
        ) from exc

    return _parse_config(data)
