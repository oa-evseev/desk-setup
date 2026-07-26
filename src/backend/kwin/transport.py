from __future__ import annotations

import asyncio
import json
import queue
import shutil
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

try:
    from dbus_next import BusType
    from dbus_next.aio import MessageBus
    from dbus_next.service import ServiceInterface, method

except ImportError as exc:
    raise RuntimeError(
        "The KWin backend requires dbus-next. "
        "Install it with: python -m pip install dbus-next"
    ) from exc


KWIN_SERVICE = "org.kde.KWin"
KWIN_SCRIPTING_PATH = "/Scripting"
KWIN_SCRIPTING_INTERFACE = "org.kde.kwin.Scripting"
KWIN_SCRIPT_INTERFACE = "org.kde.kwin.Script"

REPLY_INTERFACE = "org.desksetup.KWinReply"
RUNTIME_TEMPLATE = (
    Path(__file__).resolve().parent
    / "runtime.js"
)

DEFAULT_TIMEOUT = 5.0


def _find_qdbus() -> str:
    for executable in (
        "qdbus6",
        "qdbus",
    ):
        path = shutil.which(executable)

        if path is not None:
            return path

    raise RuntimeError(
        "Neither qdbus6 nor qdbus was found"
    )


def _run_qdbus(
    *arguments: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    try:
        completed = subprocess.run(
            [
                _find_qdbus(),
                *arguments,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "qdbus timed out while communicating "
            "with KWin"
        ) from exc

    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        stdout = exc.stdout.strip()

        details = stderr or stdout or (
            f"exit status {exc.returncode}"
        )

        raise RuntimeError(
            f"KWin D-Bus call failed: {details}"
        ) from exc

    return completed.stdout.strip()


def _load_script(
    script_path: Path,
    plugin_name: str,
) -> int:
    result = _run_qdbus(
        KWIN_SERVICE,
        KWIN_SCRIPTING_PATH,
        (
            f"{KWIN_SCRIPTING_INTERFACE}"
            ".loadScript"
        ),
        str(script_path),
        plugin_name,
    )

    try:
        script_id = int(
            result.splitlines()[-1]
        )

    except (IndexError, ValueError) as exc:
        raise RuntimeError(
            "KWin returned an invalid script ID: "
            f"{result!r}"
        ) from exc

    if script_id < 0:
        raise RuntimeError(
            "KWin rejected the temporary script"
        )

    return script_id


def _run_script(
    script_id: int,
) -> None:
    _run_qdbus(
        KWIN_SERVICE,
        f"/Scripting/Script{script_id}",
        f"{KWIN_SCRIPT_INTERFACE}.run",
    )


def _stop_script(
    script_id: int,
) -> None:
    try:
        _run_qdbus(
            KWIN_SERVICE,
            f"/Scripting/Script{script_id}",
            f"{KWIN_SCRIPT_INTERFACE}.stop",
        )

    except RuntimeError:
        pass


class _ReplyInterface(ServiceInterface):
    def __init__(
        self,
        results: queue.Queue[
            str | BaseException
        ],
    ) -> None:
        super().__init__(REPLY_INTERFACE)

        self._results = results

    @method()
    def Reply(
        self,
        payload: "s",
    ) -> "b":
        self._results.put(payload)

        return True


class _ReplyServer:
    def __init__(
        self,
        service_name: str,
        object_path: str,
    ) -> None:
        self.service_name = service_name
        self.object_path = object_path

        self._results: queue.Queue[
            str | BaseException
        ] = (
            queue.Queue()
        )

        self._startup: queue.Queue[
            BaseException | None
        ] = queue.Queue(maxsize=1)

        self._loop: (
            asyncio.AbstractEventLoop | None
        ) = None

        self._stop_event: asyncio.Event | None = None

        self._startup_reported = threading.Event()
        self._stop_requested = threading.Event()

        self._thread = threading.Thread(
            target=self._thread_main,
            name="desk-setup-kwin-reply",
            daemon=True,
        )

    def __enter__(self) -> "_ReplyServer":
        self.start()

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        try:
            self.stop()

        except RuntimeError as stop_error:
            if exc_value is None:
                raise

            exc_value.add_note(
                "The D-Bus reply service also "
                f"failed to stop: {stop_error}"
            )

    def start(self) -> None:
        self._thread.start()

        try:
            result = self._startup.get(
                timeout=DEFAULT_TIMEOUT,
            )

        except queue.Empty as exc:
            try:
                self.stop()

            except RuntimeError as stop_error:
                raise RuntimeError(
                    "Timed out while starting the "
                    "temporary D-Bus reply service; "
                    "its thread did not stop"
                ) from stop_error

            raise RuntimeError(
                "Timed out while starting the "
                "temporary D-Bus reply service"
            ) from exc

        if result is not None:
            raise RuntimeError(
                "Could not start the temporary "
                "D-Bus reply service"
            ) from result

    def stop(self) -> None:
        self._stop_requested.set()

        loop = self._loop
        stop_event = self._stop_event

        if (
            loop is not None
            and stop_event is not None
            and loop.is_running()
        ):
            loop.call_soon_threadsafe(
                stop_event.set
            )

        if self._thread.is_alive():
            self._thread.join(
                timeout=DEFAULT_TIMEOUT,
            )

        if self._thread.is_alive():
            raise RuntimeError(
                "The temporary D-Bus reply "
                "service thread did not stop"
            )

    def receive(
        self,
        timeout: float,
    ) -> str:
        try:
            result = self._results.get(
                timeout=timeout,
            )

        except queue.Empty as exc:
            raise RuntimeError(
                "Timed out waiting for the "
                "KWin script reply"
            ) from exc

        if isinstance(result, BaseException):
            raise RuntimeError(
                "The temporary D-Bus reply "
                "service failed"
            ) from result

        return result

    def _thread_main(self) -> None:
        try:
            asyncio.run(
                self._serve()
            )

        except BaseException as exc:
            if self._startup_reported.is_set():
                self._results.put(exc)
            else:
                self._report_startup(exc)

    def _report_startup(
        self,
        result: BaseException | None,
    ) -> None:
        self._startup_reported.set()
        self._startup.put(result)

    async def _serve(self) -> None:
        bus = None
        exported = False

        try:
            bus = await MessageBus(
                bus_type=BusType.SESSION,
            ).connect()

            await bus.request_name(
                self.service_name
            )

            interface = _ReplyInterface(
                self._results
            )

            bus.export(
                self.object_path,
                interface,
            )

            exported = True

            self._loop = (
                asyncio.get_running_loop()
            )

            self._stop_event = asyncio.Event()

            self._report_startup(None)

            if self._stop_requested.is_set():
                self._stop_event.set()

            await self._stop_event.wait()

        finally:
            if bus is not None:
                if exported:
                    try:
                        bus.unexport(
                            self.object_path
                        )

                    except Exception:
                        pass

                try:
                    await bus.release_name(
                        self.service_name
                    )

                except Exception:
                    pass

                try:
                    bus.disconnect()

                except Exception:
                    pass


def _make_identifiers() -> tuple[
    str,
    str,
    str,
]:
    token = uuid.uuid4().hex

    service_name = (
        "org.desksetup.KWinReply."
        f"x{token}"
    )

    object_path = (
        "/org/desksetup/KWinReply/"
        f"x{token}"
    )

    plugin_name = (
        "desk-setup-"
        f"{token}"
    )

    return (
        service_name,
        object_path,
        plugin_name,
    )


def _javascript_string(
    value: str,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
    )


def _render_runtime(
    request: dict[str, Any],
    *,
    service_name: str,
    object_path: str,
) -> str:
    try:
        source = RUNTIME_TEMPLATE.read_text(
            encoding="utf-8",
        )

    except OSError as exc:
        raise RuntimeError(
            "Could not read the KWin runtime "
            f"template: {RUNTIME_TEMPLATE}"
        ) from exc

    replacements = {
        "__REQUEST_JSON__": json.dumps(
            request,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "__REPLY_SERVICE__": (
            _javascript_string(service_name)
        ),
        "__REPLY_PATH__": (
            _javascript_string(object_path)
        ),
        "__REPLY_INTERFACE__": (
            _javascript_string(
                REPLY_INTERFACE
            )
        ),
    }

    for marker, replacement in (
        replacements.items()
    ):
        if marker not in source:
            raise RuntimeError(
                "The KWin runtime template is "
                f"missing marker {marker}"
            )

        source = source.replace(
            marker,
            replacement,
        )

    return source


def _run_loaded_script(
    script_path: Path,
    plugin_name: str,
    reply_server: _ReplyServer,
) -> str:
    script_id = _load_script(
        script_path,
        plugin_name,
    )

    try:
        _run_script(script_id)

        return reply_server.receive(
            timeout=DEFAULT_TIMEOUT,
        )

    finally:
        _stop_script(script_id)


def _parse_response(
    payload: str,
) -> Any:
    try:
        response = json.loads(payload)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "KWin returned invalid JSON: "
            f"{payload!r}"
        ) from exc

    if not isinstance(response, dict):
        raise RuntimeError(
            "KWin returned an invalid response: "
            f"{response!r}"
        )

    if response.get("ok") is not True:
        error = response.get(
            "error",
            "Unknown KWin script error",
        )

        stack = response.get("stack")

        if stack:
            raise RuntimeError(
                f"{error}\n{stack}"
            )

        raise RuntimeError(
            str(error)
        )

    return response.get("result")


def _execute(
    method_name: str,
    **parameters: Any,
) -> Any:
    (
        service_name,
        object_path,
        plugin_name,
    ) = _make_identifiers()

    request = {
        "method": method_name,
        "params": parameters,
    }

    source = _render_runtime(
        request,
        service_name=service_name,
        object_path=object_path,
    )

    with tempfile.TemporaryDirectory(
        prefix="desk-setup-kwin-",
    ) as temporary_directory:
        script_path = (
            Path(temporary_directory)
            / "request.js"
        )

        try:
            script_path.write_text(
                source,
                encoding="utf-8",
            )

        except OSError as exc:
            raise RuntimeError(
                "Could not write the temporary "
                "KWin script"
            ) from exc

        with _ReplyServer(
            service_name,
            object_path,
        ) as reply_server:
            payload = _run_loaded_script(
                script_path,
                plugin_name,
                reply_server,
            )

    return _parse_response(payload)


def call(
    method_name: str,
    **parameters: Any,
) -> Any:
    return _execute(
        method_name,
        **parameters,
    )


__all__ = ["call"]
