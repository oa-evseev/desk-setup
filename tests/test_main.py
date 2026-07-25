from pathlib import Path
from unittest.mock import Mock

from src import main
from src.models import Config, Monitor, Window


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

    apply.assert_called_once_with(Path("example.yaml"))


def test_main_without_command_prints_help(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["desk-setup"])

    main.main()

    output = capsys.readouterr().out
    assert "usage:" in output
    assert "apply" in output
