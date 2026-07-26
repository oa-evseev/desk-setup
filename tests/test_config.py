from pathlib import Path

import pytest

from src.config import load_config


def write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "desk.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_complete_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    path = write_config(
        tmp_path,
        """
version: 1
monitors:
  left:
    windows:
      - exec: [firefox, --new-window, "https://example.com"]
        cwd: ~/projects
        tile: top-left
  right:
    windows: []
""",
    )

    config = load_config(path)

    assert config.version == 1
    assert list(config.monitors) == ["left", "right"]
    window = config.monitors["left"].windows[0]
    assert window.exec == [
        "firefox",
        "--new-window",
        "https://example.com",
    ]
    assert window.cwd == tmp_path / "home" / "projects"
    assert window.tile == "top-left"
    assert config.monitors["right"].windows == []


def test_windows_defaults_to_empty_list(tmp_path):
    path = write_config(
        tmp_path,
        "version: 1\nmonitors:\n  center: {}\n",
    )

    config = load_config(path)

    assert config.monitors["center"].windows == []


def test_missing_cwd_becomes_none(tmp_path):
    path = write_config(
        tmp_path,
        """
version: 1
monitors:
  center:
    windows:
      - exec: [kate]
        tile: full
""",
    )

    window = load_config(path).monitors["center"].windows[0]

    assert window.cwd is None


def test_loads_after_commands_and_expands_their_working_directories(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    path = write_config(
        tmp_path,
        """
version: 1
monitors:
  left:
    windows:
      - exec: [firefox, --new-window, "https://example.com"]
        cwd: /workspace
        tile: left
        after:
          - exec: [firefox, --new-tab, "https://chatgpt.com"]
          - exec: [notify-send, ready]
            cwd: ~/scripts
""",
    )

    window = load_config(path).monitors["left"].windows[0]

    assert [command.exec for command in window.after] == [
        ["firefox", "--new-tab", "https://chatgpt.com"],
        ["notify-send", "ready"],
    ]
    assert window.after[0].cwd is None
    assert window.after[1].cwd == tmp_path / "home" / "scripts"


def test_after_defaults_to_empty_list(tmp_path):
    path = write_config(
        tmp_path,
        """
version: 1
monitors:
  center:
    windows:
      - exec: [kate]
        tile: full
""",
    )

    window = load_config(path).monitors["center"].windows[0]

    assert window.after == []


@pytest.mark.parametrize("missing_key", ["exec"])
def test_after_command_requires_exec(tmp_path, missing_key):
    path = write_config(
        tmp_path,
        """
version: 1
monitors:
  center:
    windows:
      - exec: [kate]
        tile: full
        after:
          - cwd: /tmp
""",
    )

    with pytest.raises(KeyError, match=missing_key):
        load_config(path)


@pytest.mark.parametrize(
    "content",
    [
        "",
        "null\n",
        "[]\n",
        "- version\n- 1\n",
        '"a string"\n',
    ],
)
def test_rejects_non_mapping_document(tmp_path, content):
    path = write_config(tmp_path, content)

    with pytest.raises(
        ValueError,
        match="Configuration must be a mapping",
    ):
        load_config(path)


@pytest.mark.parametrize("version", ["null", "0", "2", '"1"'])
def test_rejects_unsupported_version(tmp_path, version):
    path = write_config(
        tmp_path,
        f"version: {version}\nmonitors: {{}}\n",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported configuration version",
    ):
        load_config(path)


@pytest.mark.parametrize(
    ("content", "missing_key"),
    [
        ("version: 1\n", "monitors"),
        (
            "version: 1\nmonitors:\n  left:\n"
            "    windows:\n      - tile: left\n",
            "exec",
        ),
        (
            "version: 1\nmonitors:\n  left:\n"
            "    windows:\n      - exec: [kate]\n",
            "tile",
        ),
    ],
)
def test_required_fields_are_required(tmp_path, content, missing_key):
    path = write_config(tmp_path, content)

    with pytest.raises(KeyError, match=missing_key):
        load_config(path)


def test_yaml_syntax_error_is_propagated(tmp_path):
    path = write_config(tmp_path, "version: [1\n")

    with pytest.raises(Exception) as error:
        load_config(path)

    assert error.type.__module__.startswith("yaml")


def test_missing_file_is_reported_by_pathlib(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "missing.yaml")
