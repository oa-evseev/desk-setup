from argparse import ArgumentParser
import os
from pathlib import Path
import sys

from .config import load_config
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

    configs = (
        sorted(directory.glob("*.yaml"))
        if directory.is_dir()
        else []
    )

    if not configs:
        print("No configurations found.")
        return

    for config in configs:
        print(config.stem)


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
    )

    subparsers = parser.add_subparsers(dest="command")

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("config", type=Path)

    subparsers.add_parser("list")

    arguments = sys.argv[1:]

    if (
        arguments
        and not arguments[0].startswith("-")
        and arguments[0] not in {
            "apply",
            "list",
        }
    ):
        arguments = [
            "apply",
            *arguments,
        ]

    args = parser.parse_args(arguments)

    match args.command:

        case "apply":
            cmd_apply(
                resolve_config_path(args.config)
            )

        case "list":
            cmd_list()

        case _:
            parser.print_help()


if __name__ == "__main__":
    main()
