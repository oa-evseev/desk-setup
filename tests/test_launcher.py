from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from src import launcher
from src.backend.types import WindowInfo
from src.models import Command, Config, Monitor, Window


def window_info(
    handle: str,
    pid: int = 0,
) -> WindowInfo:
    return WindowInfo(
        handle=handle,
        pid=pid,
    )


def test_window_handles_returns_all_handles():
    windows = [
        window_info("a"),
        window_info("b"),
    ]

    assert launcher._window_handles(windows) == {"a", "b"}


def test_new_window_handle_returns_last_new_window():
    windows = [
        window_info("old"),
        window_info("new-1"),
        window_info("new-2"),
    ]

    assert launcher._new_window_handle(windows, {"old"}) == "new-2"


def test_new_window_handle_returns_empty_when_none_is_new():
    assert launcher._new_window_handle(
        [window_info("old")],
        {"old"},
    ) == ""


def test_wait_for_window_prefers_pid_match(monkeypatch):
    process = SimpleNamespace(pid=123)
    list_windows = Mock(
        return_value=[
            window_info("other", 10),
            window_info("by-pid", 123),
            window_info("newer", 20),
        ]
    )
    monkeypatch.setattr(launcher, "list_windows", list_windows)

    result = launcher._wait_for_window(process, {"old"})

    assert result == "by-pid"
    list_windows.assert_called_once_with()


def test_wait_for_window_detects_window_from_existing_app(monkeypatch):
    process = SimpleNamespace(pid=123)
    monkeypatch.setattr(
        launcher,
        "list_windows",
        Mock(
            return_value=[
                window_info("old"),
                window_info("forwarded"),
            ]
        ),
    )

    assert launcher._wait_for_window(process, {"old"}) == "forwarded"


def test_wait_for_window_polls_until_window_appears(monkeypatch):
    process = SimpleNamespace(pid=123)
    list_windows = Mock(
        side_effect=[
            [window_info("old", 10)],
            [window_info("old", 10)],
            [
                window_info("old", 10),
                window_info("found", 123),
            ],
        ]
    )
    sleep = Mock()
    monkeypatch.setattr(launcher, "list_windows", list_windows)
    monkeypatch.setattr(launcher.time, "sleep", sleep)

    result = launcher._wait_for_window(process, {"old"})

    assert result == "found"
    assert list_windows.call_count == 3
    assert sleep.call_args_list == [
        call(launcher._POLL_INTERVAL),
        call(launcher._POLL_INTERVAL),
    ]


def test_wait_for_window_timeout_has_diagnostics(monkeypatch):
    process = SimpleNamespace(pid=777)
    monotonic = Mock(side_effect=[10.0, 26.0])
    monkeypatch.setattr(launcher.time, "monotonic", monotonic)
    monkeypatch.setattr(
        launcher,
        "list_windows",
        Mock(
            return_value=[
                window_info("old"),
                window_info("late"),
            ]
        ),
    )

    with pytest.raises(RuntimeError) as error:
        launcher._wait_for_window(process, {"old"})

    message = str(error.value)
    assert "15.0 seconds" in message
    assert "PID 777" in message
    assert "late" in message


def test_launch_window_starts_and_arranges_application(monkeypatch, tmp_path):
    window = Window(exec=["kate", "notes.txt"], cwd=tmp_path, tile="left")
    process = SimpleNamespace(pid=321)
    popen = Mock(return_value=process)
    wait = Mock(return_value="window-7")
    arrange = Mock()
    monkeypatch.setattr(
        launcher,
        "list_windows",
        Mock(return_value=[window_info("existing")]),
    )
    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    monkeypatch.setattr(launcher, "_wait_for_window", wait)
    monkeypatch.setattr(launcher, "arrange_window", arrange)

    launcher.launch_window(window, "center")

    popen.assert_called_once_with(
        ["kate", "notes.txt"],
        cwd=tmp_path,
        stdout=launcher.subprocess.DEVNULL,
        stderr=launcher.subprocess.STDOUT,
    )
    wait.assert_called_once_with(process, {"existing"})
    arrange.assert_called_once_with("window-7", window, "center")


def test_launch_window_runs_after_commands_only_after_arranging(
    monkeypatch,
    tmp_path,
):
    window = Window(
        exec=["firefox", "--new-window", "https://todoist.com"],
        cwd=tmp_path,
        tile="left",
        after=[
            Command(
                ["firefox", "--new-tab", "https://chatgpt.com"],
                None,
            ),
            Command(["notify-send", "ready"], tmp_path / "scripts"),
        ],
    )
    process = SimpleNamespace(pid=321)
    events = []

    monkeypatch.setattr(
        launcher,
        "list_windows",
        Mock(
            side_effect=lambda: (
                events.append("list")
                or [window_info("existing")]
            )
        ),
    )
    monkeypatch.setattr(
        launcher.subprocess,
        "Popen",
        Mock(
            side_effect=lambda *args, **kwargs: (
                events.append(("popen", args, kwargs))
                or process
            )
        ),
    )
    monkeypatch.setattr(
        launcher,
        "_wait_for_window",
        Mock(
            side_effect=lambda *args: (
                events.append("wait")
                or "window-7"
            )
        ),
    )
    monkeypatch.setattr(
        launcher,
        "arrange_window",
        Mock(
            side_effect=lambda *args: events.append("arrange")
        ),
    )

    launcher.launch_window(window, "left")

    assert events[0:4] == ["list", events[1], "wait", "arrange"]
    assert events[1][0] == "popen"
    assert events[4][0] == "popen"
    assert events[4][1] == (
        ["firefox", "--new-tab", "https://chatgpt.com"],
    )
    assert events[4][2]["cwd"] == tmp_path
    assert events[5][0] == "popen"
    assert events[5][1] == (["notify-send", "ready"],)
    assert events[5][2]["cwd"] == tmp_path / "scripts"
    for event in (events[4], events[5]):
        assert event[2]["stdout"] is launcher.subprocess.DEVNULL
        assert event[2]["stderr"] is launcher.subprocess.STDOUT


def test_after_command_is_not_run_when_arranging_fails(monkeypatch):
    window = Window(
        ["firefox"],
        None,
        "left",
        after=[Command(["firefox", "--new-tab", "url"], None)],
    )
    popen = Mock(return_value=SimpleNamespace(pid=1))
    monkeypatch.setattr(launcher, "list_windows", Mock(return_value=[]))
    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    monkeypatch.setattr(
        launcher,
        "_wait_for_window",
        Mock(return_value="window"),
    )
    monkeypatch.setattr(
        launcher,
        "arrange_window",
        Mock(side_effect=RuntimeError("cannot arrange")),
    )

    with pytest.raises(RuntimeError, match="cannot arrange"):
        launcher.launch_window(window, "left")

    assert popen.call_count == 1


def test_launch_visits_monitors_and_windows_in_configuration_order(monkeypatch):
    first = Window(["one"], None, "left")
    second = Window(["two"], None, "right")
    third = Window(["three"], None, "full")
    config = Config(
        version=1,
        monitors={
            "left": Monitor([first, second]),
            "empty": Monitor([]),
            "right": Monitor([third]),
        },
    )
    launch_window = Mock()
    monkeypatch.setattr(launcher, "launch_window", launch_window)

    launcher.launch(config)

    assert launch_window.call_args_list == [
        call(first, "left"),
        call(second, "left"),
        call(third, "right"),
    ]
