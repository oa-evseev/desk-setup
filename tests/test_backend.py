from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from src.backend import dispatcher
from src.backend import kwin
from src.models import Window


@pytest.mark.parametrize(
    "desktop",
    ["KDE", "kde", "KDE:GNOME", "ubuntu:KDE", "plasma-kde"],
)
def test_detect_window_manager_recognises_kde(monkeypatch, desktop):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", desktop)

    assert dispatcher.detect_window_manager() is kwin


@pytest.mark.parametrize("desktop", ["", "GNOME", "XFCE"])
def test_detect_window_manager_rejects_other_desktops(monkeypatch, desktop):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", desktop)

    with pytest.raises(
        NotImplementedError,
        match="Unsupported desktop environment",
    ):
        dispatcher.detect_window_manager()


def test_dispatcher_delegates_all_operations(monkeypatch):
    backend = SimpleNamespace(
        list_windows=Mock(return_value=[{"handle": "handle"}]),
        arrange_window=Mock(),
    )
    monkeypatch.setattr(dispatcher, "detect_window_manager", lambda: backend)
    window = Window(["kate"], None, "left")

    assert dispatcher.list_windows() == [{"handle": "handle"}]
    dispatcher.arrange_window("handle", window, "center")

    backend.list_windows.assert_called_once_with()
    backend.arrange_window.assert_called_once_with("handle", window, "center")


def test_arrange_window_moves_tiles_and_activates(monkeypatch):
    output = {"name": "DP-1", "x": 0, "y": 0, "width": 1200, "height": 800}
    window = Window(["kate"], None, "left")
    operations = []
    monkeypatch.setattr(kwin, "list_outputs", lambda: [output])
    monkeypatch.setattr(
        kwin,
        "move_resize_window",
        lambda handle, **geometry: operations.append(
            ("move", handle, geometry)
        ),
    )
    monkeypatch.setattr(
        kwin,
        "quick_tile_window",
        lambda handle, tile: operations.append(("tile", handle, tile)),
    )
    monkeypatch.setattr(
        kwin,
        "activate_window",
        lambda handle: operations.append(("activate", handle)),
    )

    kwin.arrange_window("w1", window, "DP-1")

    assert operations == [
        (
            "move",
            "w1",
            {"x": 0, "y": 0, "width": 600, "height": 800},
        ),
        ("tile", "w1", "left"),
        ("activate", "w1"),
    ]


def test_arrange_window_skips_quick_tile_for_custom_geometry(monkeypatch):
    output = {"name": "DP-1", "x": 0, "y": 0, "width": 100, "height": 100}
    window = Window(["kate"], None, [0.1, 0.2, 0.3, 0.4])
    move = Mock()
    quick_tile = Mock()
    activate = Mock()
    monkeypatch.setattr(kwin, "list_outputs", Mock(return_value=[output]))
    monkeypatch.setattr(kwin, "move_resize_window", move)
    monkeypatch.setattr(kwin, "quick_tile_window", quick_tile)
    monkeypatch.setattr(kwin, "activate_window", activate)

    kwin.arrange_window("w1", window, "DP-1")

    move.assert_called_once_with(
        "w1",
        x=10,
        y=20,
        width=30,
        height=40,
    )
    quick_tile.assert_not_called()
    activate.assert_called_once_with("w1")
