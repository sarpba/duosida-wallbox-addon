#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
PROBE = ROOT / "duosida_probe.py"

STATE = {
    "ok": False,
    "data": {},
    "error": "No data collected yet.",
    "updated_at": None,
    "duration": None,
    "last_command": None,
}
STATE_LOCK = threading.Lock()
POLL_LOCK = threading.Lock()


def run_probe(charger_host: str, duration: int) -> dict:
    started = time.time()
    cmd = [
        sys.executable,
        str(PROBE),
        "--host",
        charger_host,
        "--mode",
        "session",
        "--duration",
        str(duration),
        "--trigger",
        "meter-values",
        "--session-trigger",
        "status",
        "--json",
    ]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=duration + 10,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"probe exited {proc.returncode}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        output = proc.stdout.strip() or proc.stderr.strip()
        raise RuntimeError(f"probe did not return JSON: {output}") from exc
    return {
        "ok": True,
        "data": data,
        "error": None,
        "updated_at": time.time(),
        "duration": round(time.time() - started, 2),
    }


def run_probe_command(cmd: list[str], duration: int) -> dict:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=duration + 10,
        check=False,
    )
    output = proc.stdout.strip() or proc.stderr.strip()
    if proc.returncode != 0:
        raise RuntimeError(output or f"probe exited {proc.returncode}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        if output == "No frames received.":
            raise RuntimeError("No response from charger on TCP/9988. Close the mobile app, check LAN/AP mode, then refresh once before saving.") from exc
        raise RuntimeError(f"probe did not return JSON: {output}") from exc


def set_max_current(charger_host: str, duration: int, max_current: float, client_id: str | None) -> dict:
    started = time.time()
    command_client_id = client_id or "From Python"
    cmd = [
        sys.executable,
        str(PROBE),
        "--host",
        charger_host,
        "--mode",
        "set-max-current-direct",
        "--client-id",
        command_client_id,
        "--max-current",
        f"{max_current:g}",
        "--duration",
        str(max(5, min(duration, 8))),
        "--json",
    ]

    command_data: dict = {}
    command_error = None
    try:
        command_data = run_probe_command(cmd, max(5, min(duration, 8)))
    except RuntimeError as exc:
        command_error = str(exc)

    status = command_data.get("change_configuration_status")
    if status in {"Rejected", "NotSupported"}:
        raise RuntimeError(f"charger rejected configuration change: {status or 'no confirmation'}")

    verify_cmd = [
        sys.executable,
        str(PROBE),
        "--host",
        charger_host,
        "--mode",
        "pull-config",
        "--client-id",
        command_client_id,
        "--duration",
        str(max(duration, 8)),
        "--json",
    ]
    data: dict = {}
    verify_error = None
    for attempt in range(2):
        if attempt:
            time.sleep(1.5)
        try:
            data = run_probe_command(verify_cmd, max(duration, 8))
        except RuntimeError as exc:
            verify_error = str(exc)
            continue
        if data.get("config_maxWorkCurrent") is not None:
            break

    if not data:
        if status in {"Accepted", "RebootRequired"}:
            data = command_data
        else:
            raise RuntimeError(command_error or verify_error or "charger did not confirm configuration change")

    configured = data.get("config_maxWorkCurrent")
    if configured is not None and abs(float(configured) - max_current) > 0.1:
        raise RuntimeError(f"charger still reports {configured} A after saving {max_current:g} A")
    if configured is None and status in {"Accepted", "RebootRequired"}:
        data["config_maxWorkCurrent"] = max_current
    if status is None:
        status = data.get("change_configuration_status") or "Verified"

    return {
        "ok": True,
        "data": data,
        "error": None,
        "updated_at": time.time(),
        "duration": round(time.time() - started, 2),
        "last_command": {
            "type": "set_max_current",
            "value": max_current,
            "status": status,
            "updated_at": time.time(),
        },
    }


def set_charging(
    charger_host: str,
    duration: int,
    enabled: bool,
    client_id: str | None,
    id_tag: str | None = None,
    transaction_id: int | None = None,
) -> dict:
    started = time.time()
    command_client_id = client_id or "From Python"
    if enabled:
        cmd = [
            sys.executable,
            str(PROBE),
            "--host",
            charger_host,
            "--mode",
            "start",
            "--client-id",
            command_client_id,
            "--id-tag",
            id_tag or "HA",
            "--duration",
            str(max(5, min(duration, 8))),
            "--json",
        ]
        command_type = "start_charging"
        command_value: object = id_tag or "HA"
    else:
        if transaction_id is None:
            raise RuntimeError("charger did not report an active transaction id")
        cmd = [
            sys.executable,
            str(PROBE),
            "--host",
            charger_host,
            "--mode",
            "stop",
            "--client-id",
            command_client_id,
            "--transaction-id",
            str(transaction_id),
            "--duration",
            str(max(5, min(duration, 8))),
            "--json",
        ]
        command_type = "stop_charging"
        command_value = transaction_id

    data = run_probe_command(cmd, max(5, min(duration, 8)))
    return {
        "ok": True,
        "data": data,
        "error": None,
        "updated_at": time.time(),
        "duration": round(time.time() - started, 2),
        "last_command": {
            "type": command_type,
            "value": command_value,
            "status": "Sent",
            "updated_at": time.time(),
        },
    }


def poll_once(charger_host: str, duration: int) -> None:
    if not POLL_LOCK.acquire(blocking=False):
        return
    try:
        try:
            result = run_probe(charger_host, duration)
        except Exception as exc:
            with STATE_LOCK:
                STATE["ok"] = False
                STATE["error"] = str(exc)
                STATE["updated_at"] = time.time()
                STATE["duration"] = None
        else:
            with STATE_LOCK:
                STATE.update(result)
    finally:
        POLL_LOCK.release()


def poll_loop(charger_host: str, duration: int, interval: int) -> None:
    while True:
        poll_once(charger_host, duration)
        time.sleep(interval)


def content_type(path: Path) -> str:
    if path.suffix == ".html":
        return "text/html; charset=utf-8"
    if path.suffix == ".css":
        return "text/css; charset=utf-8"
    if path.suffix == ".js":
        return "application/javascript; charset=utf-8"
    if path.suffix == ".json":
        return "application/json; charset=utf-8"
    return "application/octet-stream"


class DashboardHandler(BaseHTTPRequestHandler):
    charger_host = "192.168.7.140"
    probe_duration = 15

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("invalid JSON body") from exc
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            with STATE_LOCK:
                payload = dict(STATE)
            if payload["updated_at"] is not None:
                payload["age"] = round(time.time() - payload["updated_at"], 1)
            else:
                payload["age"] = None
            self.send_json(payload)
            return
        if parsed.path == "/api/refresh":
            threading.Thread(
                target=poll_once,
                args=(self.charger_host, self.probe_duration),
                daemon=True,
            ).start()
            self.send_json({"ok": True, "refreshing": True})
            return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            return

        requested = "index.html" if parsed.path in {"", "/"} else parsed.path.lstrip("/")
        path = (WEB_ROOT / requested).resolve()
        if not str(path).startswith(str(WEB_ROOT.resolve())) or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type(path))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/config/max-current":
            self.handle_set_max_current()
            return
        if parsed.path == "/api/charging/start":
            self.handle_set_charging(True)
            return
        if parsed.path == "/api/charging/stop":
            self.handle_set_charging(False)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def handle_set_max_current(self) -> None:
        try:
            payload = self.read_json()
            max_current = float(payload.get("value"))
        except (TypeError, ValueError) as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        if not 6 <= max_current <= 32:
            self.send_json({"ok": False, "error": "value must be between 6 and 32 A"}, HTTPStatus.BAD_REQUEST)
            return

        with STATE_LOCK:
            data = STATE.get("data") if isinstance(STATE.get("data"), dict) else {}
            client_id = data.get("client_id") or data.get("chargePointSerialNumber")
            client_id = str(client_id) if client_id else None

        try:
            with POLL_LOCK:
                result = set_max_current(self.charger_host, self.probe_duration, max_current, client_id)
        except Exception as exc:
            with STATE_LOCK:
                STATE["ok"] = False
                STATE["error"] = str(exc)
                STATE["updated_at"] = time.time()
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return

        with STATE_LOCK:
            STATE.update(result)
        self.send_json({"ok": True, "state": result})

    def handle_set_charging(self, enabled: bool) -> None:
        try:
            payload = self.read_json()
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        with STATE_LOCK:
            data = STATE.get("data") if isinstance(STATE.get("data"), dict) else {}
            client_id = data.get("client_id") or data.get("chargePointSerialNumber")
            client_id = str(client_id) if client_id else None
            transaction_id = payload.get("transaction_id") or data.get("transaction_id") or data.get("vendor_transactionId")
            if transaction_id in {"", 0, "0"}:
                transaction_id = None

        try:
            parsed_transaction_id = int(transaction_id) if transaction_id is not None else None
        except (TypeError, ValueError):
            self.send_json({"ok": False, "error": "transaction_id must be an integer"}, HTTPStatus.BAD_REQUEST)
            return

        id_tag = payload.get("id_tag")
        if id_tag is not None and not isinstance(id_tag, str):
            self.send_json({"ok": False, "error": "id_tag must be a string"}, HTTPStatus.BAD_REQUEST)
            return

        try:
            with POLL_LOCK:
                result = set_charging(
                    self.charger_host,
                    self.probe_duration,
                    enabled,
                    client_id,
                    id_tag=id_tag,
                    transaction_id=parsed_transaction_id,
                )
        except Exception as exc:
            with STATE_LOCK:
                STATE["ok"] = False
                STATE["error"] = str(exc)
                STATE["updated_at"] = time.time()
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return

        with STATE_LOCK:
            current_data = STATE.get("data") if isinstance(STATE.get("data"), dict) else {}
            merged_data = dict(current_data)
            if isinstance(result.get("data"), dict):
                merged_data.update(result["data"])
            result["data"] = merged_data
            STATE.update(result)
        self.send_json({"ok": True, "state": result})

def main() -> None:
    parser = argparse.ArgumentParser(description="Duosida charger local dashboard.")
    parser.add_argument("--charger-host", default="192.168.7.140")
    parser.add_argument("--listen", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--probe-duration", type=int, default=15)
    args = parser.parse_args()

    DashboardHandler.charger_host = args.charger_host
    DashboardHandler.probe_duration = args.probe_duration

    threading.Thread(
        target=poll_loop,
        args=(args.charger_host, args.probe_duration, args.interval),
        daemon=True,
    ).start()

    server = ThreadingHTTPServer((args.listen, args.port), DashboardHandler)
    print(f"Serving Duosida dashboard at http://{args.listen}:{args.port}")
    print(f"Polling charger {args.charger_host} every {args.interval}s")
    server.serve_forever()


if __name__ == "__main__":
    main()
