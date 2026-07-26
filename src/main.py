from argparse import ArgumentParser, RawDescriptionHelpFormatter
import os
from pathlib import Path
import sys

from .config import ConfigError, load_config
from .launcher import launch


def config_directory() -> Path:

    config_home = os.environ.get(
        "XDG_CONFIG_HOME",
    )

    if config_home:
        return Path(config_home) / "desk-setup"

    return (
        Path.home()
        / ".config"
        / "desk-setup"
    )


def resolve_config_path(path: Path) -> Path:

    if (
        path.is_absolute()
        or path.parent != Path(".")
    ):
        return path

    name = path.name

    if not name.endswith(".yaml"):
        name = f"{name}.yaml"

    return config_directory() / name


def cmd_list() -> None:

    directory = config_directory()
    color = _use_color()

    configs = (
        sorted(directory.glob("*.yaml"))
        if directory.is_dir()
        else []
    )

    print(
        "Configurations in "
        f"{_style(str(directory), '1;34', color)}:"
    )

    if not configs:
        print("  No configurations found.")
        return

    entries: list[tuple[str, str | None, bool]] = []

    for path in configs:
        try:
            description = load_config(path).description
            valid = True
        except ConfigError:
            description = "[invalid configuration]"
            valid = False

        entries.append((path.stem, description, valid))

    width = max(len(name) for name, _, _ in entries)

    for name, description, valid in entries:
        styled_name = _style(name, "1;36", color)

        if description is None:
            print(f"  {styled_name}")
            continue

        detail = (
            description
            if valid
            else _style(description, "1;31", color)
        )
        padding = " " * (width - len(name))
        print(f"  {styled_name}{padding}  {detail}")


def _use_color() -> bool:
    return (
        sys.stdout.isatty()
        and "NO_COLOR" not in os.environ
    )


def _style(
    text: str,
    code: str,
    enabled: bool,
) -> str:
    if not enabled:
        return text

    return f"\033[{code}m{text}\033[0m"


def cmd_apply(config_path: Path) -> None:

    config = load_config(config_path)

    print(f"Applying configuration: {config_path}")
    print(f"Version: {config.version}")
    print()

    for monitor_name, monitor in config.monitors.items():

        print(f"Monitor '{monitor_name}'")

        if not monitor.windows:
            print("  (no windows)")
            print()
            continue

        for window in monitor.windows:

            command = " ".join(window.exec)

            print(f"  Launch: {command}")

            if window.cwd is not None:
                print(f"    cwd : {window.cwd}")

            print(f"    tile: {window.tile}")

        print()

    launch(config)

def main() -> None:

    parser = ArgumentParser(
        prog="desk-setup",
        description=(
            "Launch applications and arrange their windows "
            "from a YAML configuration."
        ),
        epilog=(
            "Common commands:\n"
            "  desk-setup list          List configurations\n"
            "  desk-setup coding        Apply the 'coding' configuration\n"
            "  desk-setup apply coding  Explicit apply form\n"
            "\n"
            "Project: https://github.com/oa-evseev/desk-setup"
        ),
        formatter_class=RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command")

    apply_parser = subparsers.add_parser(
        "apply",
        help="Apply a configuration",
    )
    apply_parser.add_argument("config", type=Path)

    subparsers.add_parser(
        "list",
        help="List available configurations",
    )
    subparsers.add_parser(
        "help",
        help="Show this help message",
    )

    arguments = sys.argv[1:]

    if (
        arguments
        and not arguments[0].startswith("-")
        and arguments[0] not in {
            "apply",
            "help",
            "list",
        }
    ):
        arguments = [
            "apply",
            *arguments,
        ]

    args = parser.parse_args(arguments)

    try:
        match args.command:

            case "apply":
                cmd_apply(
                    resolve_config_path(args.config)
                )

            case "list":
                cmd_list()

            case "help":
                parser.print_help()

            case _:
                parser.print_help()

    except ConfigError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
