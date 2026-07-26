import json
import queue
import subprocess
from unittest.mock import Mock

import pytest

from src.backend.kwin import transport as client


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
    monkeypatch.setattr(client, "_find_qdbus", lambda: "/bin/qdbus6")

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
        client,
        "_find_qdbus",
        lambda: "/bin/qdbus6",
    )
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
    monkeypatch.setattr(
        client,
        "_find_qdbus",
        lambda: "/bin/qdbus6",
    )
    monkeypatch.setattr(
        client.subprocess,
        "run",
        Mock(side_effect=error),
    )

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


def test_reply_server_stops_after_startup_timeout(monkeypatch):
    server = client._ReplyServer(
        "org.example",
        "/org/example",
    )
    server._thread = Mock()
    server._startup = Mock(
        get=Mock(side_effect=queue.Empty),
    )
    stop = Mock()
    monkeypatch.setattr(server, "stop", stop)

    with pytest.raises(
        RuntimeError,
        match="Timed out while starting",
    ):
        server.start()

    stop.assert_called_once_with()


def test_reply_server_receive_surfaces_background_error():
    server = client._ReplyServer(
        "org.example",
        "/org/example",
    )
    server._results.put(
        RuntimeError("D-Bus connection lost")
    )

    with pytest.raises(
        RuntimeError,
        match="reply service failed",
    ) as error:
        server.receive(timeout=0.1)

    assert isinstance(
        error.value.__cause__,
        RuntimeError,
    )
    assert "D-Bus connection lost" in str(
        error.value.__cause__
    )


def test_reply_server_stop_rejects_stuck_thread():
    server = client._ReplyServer(
        "org.example",
        "/org/example",
    )
    server._thread = Mock()
    server._thread.is_alive.return_value = True

    with pytest.raises(
        RuntimeError,
        match="did not stop",
    ):
        server.stop()

    server._thread.join.assert_called_once_with(
        timeout=client.DEFAULT_TIMEOUT,
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("not-json", "invalid JSON"),
        ("[]", "invalid response"),
        ('{"ok": false, "error": "broken"}', "broken"),
        (
            '{"ok": false, "error": "broken", "stack": "trace"}',
            "broken\ntrace",
        ),
    ],
)
def test_parse_response_rejects_invalid_or_failed_replies(
    payload,
    message,
):
    with pytest.raises(RuntimeError, match=message):
        client._parse_response(payload)


def test_parse_response_returns_success_result():
    assert client._parse_response(
        '{"ok": true, "result": {"handle": "w1"}}'
    ) == {"handle": "w1"}


def test_run_loaded_script_always_stops_script(monkeypatch):
    reply_server = Mock()
    run = Mock(side_effect=RuntimeError("run failed"))
    stop = Mock()
    monkeypatch.setattr(
        client,
        "_load_script",
        Mock(return_value=17),
    )
    monkeypatch.setattr(client, "_run_script", run)
    monkeypatch.setattr(client, "_stop_script", stop)

    with pytest.raises(RuntimeError, match="run failed"):
        client._run_loaded_script(
            client.Path("/tmp/request.js"),
            "plugin",
            reply_server,
        )

    stop.assert_called_once_with(17)
