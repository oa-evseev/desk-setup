from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from src import launcher
from src.models import Config, Monitor, Window


def test_window_handles_ignores_empty_and_missing_handles():
    windows = [
        {"handle": "a"},
        {"handle": 42},
        {"handle": ""},
        {"title": "no handle"},
        {"handle": None},
    ]

    assert launcher._window_handles(windows) == {"a", "42"}


def test_new_window_handle_returns_last_new_window():
    windows = [
        {"handle": "old"},
        {"handle": "new-1"},
        {"handle": "new-2"},
    ]

    assert launcher._new_window_handle(windows, {"old"}) == "new-2"


def test_new_window_handle_returns_empty_when_none_is_new():
    assert launcher._new_window_handle(
        [{"handle": "old"}, {"handle": ""}],
        {"old"},
    ) == ""


def test_wait_for_window_prefers_pid_match(monkeypatch):
    process = SimpleNamespace(pid=123)
    find_window = Mock(return_value="by-pid")
    list_windows = Mock()
    monkeypatch.setattr(launcher, "find_window", find_window)
    monkeypatch.setattr(launcher, "list_windows", list_windows)

    result = launcher._wait_for_window(process, {"old"})

    assert result == "by-pid"
    find_window.assert_called_once_with(123)
    list_windows.assert_not_called()


def test_wait_for_window_detects_window_from_existing_app(monkeypatch):
    process = SimpleNamespace(pid=123)
    monkeypatch.setattr(launcher, "find_window", Mock(return_value=""))
    monkeypatch.setattr(
        launcher,
        "list_windows",
        Mock(return_value=[{"handle": "old"}, {"handle": "forwarded"}]),
    )

    assert launcher._wait_for_window(process, {"old"}) == "forwarded"


def test_wait_for_window_polls_until_window_appears(monkeypatch):
    process = SimpleNamespace(pid=123)
    find_window = Mock(side_effect=["", "", "found"])
    list_windows = Mock(return_value=[{"handle": "old"}])
    sleep = Mock()
    monkeypatch.setattr(launcher, "find_window", find_window)
    monkeypatch.setattr(launcher, "list_windows", list_windows)
    monkeypatch.setattr(launcher.time, "sleep", sleep)

    result = launcher._wait_for_window(process, {"old"})

    assert result == "found"
    assert find_window.call_count == 3
    assert list_windows.call_count == 2
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
        Mock(return_value=[{"handle": "old"}, {"handle": "late"}]),
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
        Mock(return_value=[{"handle": "existing"}]),
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

