from unittest.mock import Mock, call

import pytest

from src.backend.kwin import client
from src.backend.types import OutputInfo, WindowInfo


@pytest.mark.parametrize(
    ("function", "result"),
    [
        (client.list_windows, {}),
        (client.list_outputs, {}),
    ],
)
def test_read_methods_validate_response_type(
    monkeypatch,
    function,
    result,
):
    monkeypatch.setattr(
        client,
        "call",
        Mock(return_value=result),
    )

    with pytest.raises(RuntimeError, match="invalid"):
        function()


def test_list_windows_parses_typed_items(monkeypatch):
    monkeypatch.setattr(
        client,
        "call",
        Mock(
            return_value=[
                {
                    "handle": "window-1",
                    "pid": 42,
                    "title": "ignored",
                }
            ]
        ),
    )

    assert client.list_windows() == [
        WindowInfo(
            handle="window-1",
            pid=42,
        )
    ]


@pytest.mark.parametrize(
    ("item", "field"),
    [
        ({}, "handle"),
        ({"handle": 12, "pid": 42}, "handle"),
        ({"handle": "w", "pid": "42"}, "pid"),
    ],
)
def test_list_windows_rejects_malformed_items(
    monkeypatch,
    item,
    field,
):
    monkeypatch.setattr(
        client,
        "call",
        Mock(return_value=[item]),
    )

    with pytest.raises(
        RuntimeError,
        match=rf"window list item 0\.{field}",
    ):
        client.list_windows()


def test_list_outputs_parses_typed_items(monkeypatch):
    monkeypatch.setattr(
        client,
        "call",
        Mock(
            return_value=[
                {
                    "name": "DP-1",
                    "x": -1920,
                    "y": 0,
                    "width": 1920,
                    "height": 1080,
                    "enabled": True,
                    "scale": 1.5,
                }
            ]
        ),
    )

    assert client.list_outputs() == [
        OutputInfo(
            name="DP-1",
            x=-1920.0,
            y=0.0,
            width=1920.0,
            height=1080.0,
            enabled=True,
        )
    ]


@pytest.mark.parametrize(
    ("item", "message"),
    [
        (
            {
                "name": "DP-1",
                "x": 0,
                "y": 0,
                "width": "wide",
                "height": 100,
            },
            r"item 0\.width",
        ),
        (
            {
                "name": "DP-1",
                "x": 0,
                "y": 0,
                "width": 0,
                "height": 100,
            },
            "width and height must be positive",
        ),
        (
            {
                "name": "DP-1",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 100,
                "enabled": "yes",
            },
            r"item 0\.enabled",
        ),
    ],
)
def test_list_outputs_rejects_malformed_items(
    monkeypatch,
    item,
    message,
):
    monkeypatch.setattr(
        client,
        "call",
        Mock(return_value=[item]),
    )

    with pytest.raises(RuntimeError, match=message):
        client.list_outputs()


def test_client_builds_expected_requests(monkeypatch):
    call_mock = Mock(
        side_effect=[1, 0, "yes"],
    )
    monkeypatch.setattr(
        client,
        "call",
        call_mock,
    )

    assert client.move_resize_window(
        "w",
        x=1,
        y=2,
        width=3,
        height=4,
    ) is True
    assert client.quick_tile_window(
        "w",
        "left",
    ) is False
    assert client.activate_window("w") is True

    assert call_mock.call_args_list == [
        call(
            "moveResizeWindow",
            handle="w",
            x=1,
            y=2,
            width=3,
            height=4,
        ),
        call(
            "quickTileWindow",
            handle="w",
            tile="left",
        ),
        call(
            "activateWindow",
            handle="w",
        ),
    ]
