import json
import subprocess
from unittest.mock import Mock, call

import pytest

from src.backend.kwin import client


def test_find_qdbus_prefers_qdbus6(monkeypatch):
    monkeypatch.setattr(
        client.shutil,
        "which",
        lambda name: f"/usr/bin/{name}",
    )

    assert client._find_qdbus() == "/usr/bin/qdbus6"


def test_find_qdbus_falls_back_to_qdbus(monkeypatch):
    monkeypatch.setattr(
        client.shutil,
        "which",
        lambda name: None if name == "qdbus6" else "/usr/bin/qdbus",
    )

    assert client._find_qdbus() == "/usr/bin/qdbus"


def test_find_qdbus_reports_missing_executable(monkeypatch):
    monkeypatch.setattr(client.shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError, match="Neither qdbus6 nor qdbus"):
        client._find_qdbus()


def test_run_qdbus_builds_command_and_strips_output(monkeypatch):
    run = Mock(
        return_value=subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="  result\n",
            stderr="",
        )
    )
    monkeypatch.setattr(client.subprocess, "run", run)
    monkeypatch.setattr(client, "QDBUS", "/bin/qdbus6")

    result = client._run_qdbus("service", "/path", "method", timeout=2.5)

    assert result == "result"
    run.assert_called_once_with(
        ["/bin/qdbus6", "service", "/path", "method"],
        check=True,
        capture_output=True,
        text=True,
        timeout=2.5,
    )


def test_run_qdbus_translates_timeout(monkeypatch):
    monkeypatch.setattr(
        client.subprocess,
        "run",
        Mock(side_effect=subprocess.TimeoutExpired(["qdbus"], 5)),
    )

    with pytest.raises(RuntimeError, match="qdbus timed out"):
        client._run_qdbus("service")


@pytest.mark.parametrize(
    ("stderr", "stdout", "expected"),
    [
        ("permission denied\n", "", "permission denied"),
        ("", "remote error\n", "remote error"),
        ("", "", "exit status 7"),
    ],
)
def test_run_qdbus_translates_process_failure(
    monkeypatch, stderr, stdout, expected
):
    error = subprocess.CalledProcessError(
        7,
        ["qdbus"],
        output=stdout,
        stderr=stderr,
    )
    monkeypatch.setattr(client.subprocess, "run", Mock(side_effect=error))

    with pytest.raises(RuntimeError, match=expected):
        client._run_qdbus("service")


@pytest.mark.parametrize(
    ("result", "expected"),
    [("7", 7), ("some diagnostic\n42\n", 42)],
)
def test_load_script_parses_script_id(monkeypatch, result, expected):
    monkeypatch.setattr(client, "_run_qdbus", Mock(return_value=result))

    assert client._load_script(client.Path("/tmp/a.js"), "plugin") == expected


@pytest.mark.parametrize("result", ["", "not-a-number", "-1"])
def test_load_script_rejects_invalid_id(monkeypatch, result):
    monkeypatch.setattr(client, "_run_qdbus", Mock(return_value=result))

    with pytest.raises(RuntimeError):
        client._load_script(client.Path("/tmp/a.js"), "plugin")


def test_stop_script_is_best_effort(monkeypatch):
    monkeypatch.setattr(
        client,
        "_run_qdbus",
        Mock(side_effect=RuntimeError("KWin is gone")),
    )

    client._stop_script(10)


def test_make_identifiers_returns_valid_unique_identifiers():
    first = client._make_identifiers()
    second = client._make_identifiers()

    assert first != second
    service, path, plugin = first
    assert service.startswith("org.desksetup.KWinReply.x")
    assert path.startswith("/org/desksetup/KWinReply/x")
    assert plugin.startswith("desk-setup-")


def test_render_runtime_embeds_json_and_escapes_strings(tmp_path, monkeypatch):
    template = tmp_path / "runtime.js"
    template.write_text(
        "const r=__REQUEST_JSON__;"
        "const s=__REPLY_SERVICE__;"
        "const p=__REPLY_PATH__;"
        "const i=__REPLY_INTERFACE__;",
        encoding="utf-8",
    )
    monkeypatch.setattr(client, "RUNTIME_TEMPLATE", template)

    source = client._render_runtime(
        {"method": "say", "params": {"text": 'Привет "KWin"'}},
        service_name='org.example."quoted"',
        object_path="/org/example/path",
    )

    assert "__REQUEST_JSON__" not in source
    assert "Привет" in source
    assert '\\"KWin\\"' in source
    assert json.dumps('org.example."quoted"') in source
    assert json.dumps(client.REPLY_INTERFACE) in source


def test_render_runtime_requires_every_marker(tmp_path, monkeypatch):
    template = tmp_path / "runtime.js"
    template.write_text("__REQUEST_JSON__", encoding="utf-8")
    monkeypatch.setattr(client, "RUNTIME_TEMPLATE", template)

    with pytest.raises(RuntimeError, match="missing marker"):
        client._render_runtime(
            {"method": "x"},
            service_name="org.example",
            object_path="/org/example",
        )


@pytest.mark.parametrize(
    ("function", "result"),
    [
        (client.list_windows, {}),
        (client.list_outputs, {}),
        (client.get_window_geometry, []),
    ],
)
def test_public_read_methods_validate_response_type(
    monkeypatch, function, result
):
    monkeypatch.setattr(client, "call", Mock(return_value=result))

    with pytest.raises(RuntimeError, match="invalid"):
        if function is client.get_window_geometry:
            function("handle")
        else:
            function()


def test_get_window_geometry_converts_fields_to_int(monkeypatch):
    monkeypatch.setattr(
        client,
        "call",
        Mock(
            return_value={
                "x": "1",
                "y": 2.9,
                "width": "300",
                "height": 400,
            }
        ),
    )

    assert client.get_window_geometry("h") == {
        "x": 1,
        "y": 2,
        "width": 300,
        "height": 400,
    }


def test_client_wrappers_build_expected_requests(monkeypatch):
    call_mock = Mock(side_effect=[None, "42", 1, 0, "yes", ""])
    monkeypatch.setattr(client, "call", call_mock)

    assert client.find_window(12) == ""
    assert client.find_window(13) == "42"
    assert client.move_resize_window(
        "w", x=1, y=2, width=3, height=4
    ) is True
    assert client.quick_tile_window("w", "left") is False
    assert client.activate_window("w") is True
    assert client.close_window("w") is False

    assert call_mock.call_args_list == [
        call("findWindow", pid=12),
        call("findWindow", pid=13),
        call(
            "moveResizeWindow",
            handle="w",
            x=1,
            y=2,
            width=3,
            height=4,
        ),
        call("quickTileWindow", handle="w", tile="left"),
        call("activateWindow", handle="w"),
        call("closeWindow", handle="w"),
    ]
