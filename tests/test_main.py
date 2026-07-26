import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

from src import main
from src.config import ConfigError
from src.models import Config, Monitor, Window


def test_list_does_not_require_qdbus(tmp_path):
    config_dir = tmp_path / "config" / "desk-setup"
    config_dir.mkdir(parents=True)
    (config_dir / "coding.yaml").write_text(
        "version: 1\n"
        "description: Daily workspace\n"
        "monitors: {}\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PATH"] = str(tmp_path / "empty-bin")
    environment["XDG_CONFIG_HOME"] = str(tmp_path / "config")

    result = subprocess.run(
        [sys.executable, "-m", "src.main", "list"],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == (
        f"Configurations in {config_dir}:\n"
        "  coding  Daily workspace\n"
    )


def test_config_directory_uses_xdg_override(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    assert main.config_directory() == tmp_path / "config" / "desk-setup"


def test_config_directory_defaults_to_home(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    assert main.config_directory() == tmp_path / ".config" / "desk-setup"


def test_resolve_config_path_uses_explicit_path_unchanged(tmp_path):
    path = tmp_path / "custom.yaml"

    assert main.resolve_config_path(path) == path


def test_resolve_config_path_expands_short_name(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    assert main.resolve_config_path(Path("coding")) == (
        tmp_path / "desk-setup" / "coding.yaml"
    )
    assert main.resolve_config_path(Path("coding.yaml")) == (
        tmp_path / "desk-setup" / "coding.yaml"
    )


def test_cmd_apply_prints_plan_and_launches(capsys, monkeypatch, tmp_path):
    config_path = tmp_path / "coding.yaml"
    config = Config(
        version=1,
        monitors={
            "center": Monitor(
                [Window(["kate", "notes.txt"], Path("/work"), "left")]
            ),
            "right": Monitor([]),
        },
    )
    load = Mock(return_value=config)
    launch = Mock()
    monkeypatch.setattr(main, "load_config", load)
    monkeypatch.setattr(main, "launch", launch)

    main.cmd_apply(config_path)

    output = capsys.readouterr().out
    assert f"Applying configuration: {config_path}" in output
    assert "Version: 1" in output
    assert "Monitor 'center'" in output
    assert "Launch: kate notes.txt" in output
    assert "cwd : /work" in output
    assert "tile: left" in output
    assert "Monitor 'right'" in output
    assert "(no windows)" in output
    load.assert_called_once_with(config_path)
    launch.assert_called_once_with(config)


def test_main_apply_dispatches_to_cmd_apply(monkeypatch):
    apply = Mock()
    monkeypatch.setattr(main, "cmd_apply", apply)
    monkeypatch.setattr(
        "sys.argv",
        ["desk-setup", "apply", "example.yaml"],
    )

    main.main()

    apply.assert_called_once_with(main.resolve_config_path(Path("example.yaml")))


def test_main_configuration_name_is_shorthand_for_apply(monkeypatch):
    apply = Mock()
    monkeypatch.setattr(main, "cmd_apply", apply)
    monkeypatch.setattr(
        "sys.argv",
        ["desk-setup", "coding"],
    )

    main.main()

    apply.assert_called_once_with(
        main.resolve_config_path(Path("coding"))
    )


def test_main_list_prints_sorted_configuration_names(
    capsys,
    monkeypatch,
    tmp_path,
):
    config_dir = tmp_path / "desk-setup"
    config_dir.mkdir()
    (config_dir / "work.yaml").write_text(
        "version: 1\nmonitors: {}\n",
        encoding="utf-8",
    )
    (config_dir / "coding.yaml").write_text(
        "version: 1\n"
        "description: Development workspace\n"
        "monitors: {}\n",
        encoding="utf-8",
    )
    (config_dir / "notes.txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(main, "config_directory", lambda: config_dir)
    monkeypatch.setattr("sys.argv", ["desk-setup", "list"])

    main.main()

    assert capsys.readouterr().out.splitlines() == [
        f"Configurations in {config_dir}:",
        "  coding  Development workspace",
        "  work",
    ]


def test_main_list_marks_invalid_config_without_hiding_others(
    capsys,
    monkeypatch,
    tmp_path,
):
    config_dir = tmp_path / "desk-setup"
    config_dir.mkdir()
    (config_dir / "broken.yaml").write_text("not: valid\n", encoding="utf-8")
    (config_dir / "coding.yaml").write_text(
        "version: 1\nmonitors: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "config_directory", lambda: config_dir)
    monkeypatch.setattr("sys.argv", ["desk-setup", "list"])

    main.main()

    assert capsys.readouterr().out.splitlines() == [
        f"Configurations in {config_dir}:",
        "  broken  [invalid configuration]",
        "  coding",
    ]


def test_main_list_adds_colors_for_terminal_output(
    capsys,
    monkeypatch,
    tmp_path,
):
    config_dir = tmp_path / "desk-setup"
    config_dir.mkdir()
    (config_dir / "coding.yaml").write_text(
        "version: 1\n"
        "description: Development workspace\n"
        "monitors: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "config_directory", lambda: config_dir)
    monkeypatch.setattr(main, "_use_color", lambda: True)
    monkeypatch.setattr("sys.argv", ["desk-setup", "list"])

    main.main()

    output = capsys.readouterr().out
    assert f"\033[1;34m{config_dir}\033[0m" in output
    assert "\033[1;36mcoding\033[0m" in output
    assert "Development workspace" in output


def test_main_list_handles_missing_configuration_directory(
    capsys,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        main,
        "config_directory",
        lambda: tmp_path / "missing",
    )
    monkeypatch.setattr("sys.argv", ["desk-setup", "list"])

    main.main()

    assert capsys.readouterr().out == (
        f"Configurations in {tmp_path / 'missing'}:\n"
        "  No configurations found.\n"
    )


def test_main_without_command_prints_help(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["desk-setup"])

    main.main()

    output = capsys.readouterr().out
    assert "usage:" in output
    assert "apply" in output


def test_main_help_describes_common_commands_and_links_project(
    capsys,
    monkeypatch,
):
    apply = Mock()
    monkeypatch.setattr(main, "cmd_apply", apply)
    monkeypatch.setattr("sys.argv", ["desk-setup", "help"])

    main.main()

    output = capsys.readouterr().out
    assert "desk-setup coding" in output
    assert "desk-setup list" in output
    assert "https://github.com/oa-evseev/desk-setup" in output
    apply.assert_not_called()


def test_main_reports_configuration_error_without_traceback(
    capsys,
    monkeypatch,
):
    monkeypatch.setattr(
        main,
        "cmd_apply",
        Mock(side_effect=ConfigError("monitors.left must be a mapping")),
    )
    monkeypatch.setattr("sys.argv", ["desk-setup", "coding"])

    with pytest.raises(SystemExit) as error:
        main.main()

    assert error.value.code == 2
    stderr = capsys.readouterr().err
    assert "monitors.left must be a mapping" in stderr
    assert "Traceback" not in stderr
