from unittest.mock import Mock, call

import pytest

from src.backend.kwin import client


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
