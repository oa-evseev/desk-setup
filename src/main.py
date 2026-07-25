from argparse import ArgumentParser
from pathlib import Path

from .config import load_config


def cmd_apply(config_path: Path) -> None:

    config = load_config(config_path)

    print()
    print(f"Version: {config.version}")
    print()

    for monitor_name, monitor in config.monitors.items():

        print(f"Monitor: {monitor_name}")

        for window in monitor.windows:

            print(f"  exec : {' '.join(window.exec)}")
            print(f"  cwd  : {window.cwd}")
            print(f"  tile : {window.tile}")
            print()

        if not monitor.windows:
            print("  (empty)")
            print()


def main() -> None:

    parser = ArgumentParser()

    subparsers = parser.add_subparsers(dest="command")

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("config", type=Path)

    args = parser.parse_args()

    match args.command:

        case "apply":
            cmd_apply(args.config)

        case _:
            parser.print_help()


if __name__ == "__main__":
    main()
