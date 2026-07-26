from pathlib import Path

import pytest

from src.config import ConfigError, load_config


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


def test_after_command_requires_exec(tmp_path):
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

    with pytest.raises(
        ConfigError,
        match=r"monitors\.center\.windows\[0\]\.after\[0\]\.exec",
    ):
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
        ConfigError,
        match="configuration must be a mapping",
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

    with pytest.raises(ConfigError, match=missing_key):
        load_config(path)


def test_yaml_syntax_error_is_reported_as_config_error(tmp_path):
    path = write_config(tmp_path, "version: [1\n")

    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(path)


def test_missing_file_is_reported_as_config_error(tmp_path):
    with pytest.raises(ConfigError, match="Could not read configuration"):
        load_config(tmp_path / "missing.yaml")


@pytest.mark.parametrize(
    ("fragment", "expected_path"),
    [
        ("monitors: []", "monitors"),
        ("monitors:\n  left: null", "monitors.left"),
        (
            "monitors:\n  left:\n    windows: {}",
            "monitors.left.windows",
        ),
        (
            "monitors:\n  left:\n    windows:\n      - null",
            r"monitors.left.windows\[0\]",
        ),
        (
            "monitors:\n  left:\n    windows:\n"
            "      - exec: firefox\n        tile: left",
            r"monitors.left.windows\[0\].exec",
        ),
        (
            "monitors:\n  left:\n    windows:\n"
            "      - exec: []\n        tile: left",
            r"monitors.left.windows\[0\].exec",
        ),
        (
            "monitors:\n  left:\n    windows:\n"
            "      - exec: [firefox, 123]\n        tile: left",
            r"monitors.left.windows\[0\].exec",
        ),
        (
            "monitors:\n  left:\n    windows:\n"
            "      - exec: [firefox]\n        cwd: {}\n        tile: left",
            r"monitors.left.windows\[0\].cwd",
        ),
        (
            "monitors:\n  left:\n    windows:\n"
            "      - exec: [firefox]\n        tile: null",
            r"monitors.left.windows\[0\].tile",
        ),
        (
            "monitors:\n  left:\n    windows:\n"
            "      - exec: [firefox]\n        tile: left\n        after: {}",
            r"monitors.left.windows\[0\].after",
        ),
    ],
)
def test_invalid_nested_types_include_field_path(
    tmp_path,
    fragment,
    expected_path,
):
    path = write_config(
        tmp_path,
        f"version: 1\n{fragment}\n",
    )

    with pytest.raises(ConfigError, match=expected_path):
        load_config(path)


@pytest.mark.parametrize(
    "tile",
    [
        "[0, 0, 0.5, 1]",
        "{x: 0, y: 0, width: 0.5, height: 1}",
    ],
)
def test_loads_structured_tile_geometry(tmp_path, tile):
    path = write_config(
        tmp_path,
        "version: 1\n"
        "monitors:\n"
        "  left:\n"
        "    windows:\n"
        "      - exec: [kate]\n"
        f"        tile: {tile}\n",
    )

    window = load_config(path).monitors["left"].windows[0]

    assert window.tile is not None


def test_rejects_unknown_fields_with_exact_path(tmp_path):
    path = write_config(
        tmp_path,
        """
version: 1
monitors:
  left:
    windows:
      - exec: [kate]
        title: editor
        tile: left
""",
    )

    with pytest.raises(
        ConfigError,
        match=r"monitors\.left\.windows\[0\]\.title.*unknown",
    ):
        load_config(path)
