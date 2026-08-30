#!/usr/bin/env python3
"""demigod: webhook-driven rolling upgrades for homeportal.

1. Points Tailscale Funnel at a local listener, giving GitHub a public HTTPS URL
   without any router port-forwarding.
2. Listens for GitHub `package` webhooks, verifying the X-Hub-Signature-256 HMAC.
3. On a newly published homeportal image, rolls the container forward:
   docker compose pull && docker compose up -d
"""

import argparse
import hashlib
import hmac
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# where the compose project lives. Host/uv dev mode: repo root. In the
# container: /app, where a baked copy of docker-compose.yml ships in the image.
COMPOSE_DIR = Path(
    os.environ.get("DEMIGOD_COMPOSE_DIR")
    or Path(__file__).resolve().parents[2]
)
PACKAGE = "homeportal"
SECRET_FILE = Path.home() / ".config" / "demigod" / "webhook-secret"

deploy_lock = threading.Lock()


def log(*parts):
    stamp = datetime.now(timezone.utc).astimezone().strftime("%H:%M:%S")
    print(stamp, *parts, flush=True)


def load_secret() -> bytes:
    env = os.environ.get("DEMIGOD_WEBHOOK_SECRET")
    if env:
        return env.encode()
    if SECRET_FILE.is_file():
        return SECRET_FILE.read_text().strip().encode()
    sys.exit(
        "No webhook secret found.\n"
        "Set DEMIGOD_WEBHOOK_SECRET, or write it to "
        f"{SECRET_FILE} (chmod 600).\n"
        "Generate one with: openssl rand -hex 32"
    )


def setup_funnel(port: int):
    """Publish the listener via Tailscale Funnel; returns the public URL or None."""
    try:
        subprocess.run(
            ["tailscale", "funnel", "--bg", f"localhost:{port}"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        log("tailscale CLI not found; skipping funnel setup")
        return None
    except subprocess.CalledProcessError as e:
        log("funnel setup failed:")
        log(e.stderr.strip())
        log("(run `tailscale funnel` once interactively to enable HTTPS certs)")
        return None

    url = None
    try:
        status = json.loads(
            subprocess.run(
                ["tailscale", "status", "--json"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )
        dns = (status.get("Self", {}).get("DNSName") or "").rstrip(".")
        if dns:
            url = f"https://{dns}/webhook"
    except Exception as e:
        log(f"could not read funnel URL: {e}")

    if url:
        log(f"funnel live: POST {url}")
    return url


def deploy(dry_run: bool):
    if not deploy_lock.acquire(blocking=False):
        log("deploy already in progress; ignoring trigger")
        return
    try:
        # target the portal service only: recreating the demigod service
        # would kill the compose client running inside it mid-deploy
        steps = [
            ["docker", "compose", "pull", "portal"],
            ["docker", "compose", "up", "-d", "portal"],
            ["docker", "image", "prune", "-f"],
        ]
        log("rolling upgrade starting")
        for cmd in steps:
            log("$", " ".join(cmd))
            if dry_run:
                continue
            result = subprocess.run(
                cmd, cwd=COMPOSE_DIR, capture_output=True, text=True
            )
            for stream in (result.stdout, result.stderr):
                for line in stream.strip().splitlines():
                    log("   ", line)
            if result.returncode != 0:
                log(f"deploy aborted: '{cmd[2]}' exited {result.returncode}")
                return
        log("deploy complete")
    finally:
        deploy_lock.release()


def make_handler(secret: bytes, dry_run: bool):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, code, payload):
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/healthz":
                self._json(200, {"ok": True})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length)

            expected = (
                "sha256="
                + hmac.new(secret, body, hashlib.sha256).hexdigest()
            )
            actual = self.headers.get("X-Hub-Signature-256", "")
            if not hmac.compare_digest(actual, expected):
                log("rejected: bad signature from", self.client_address[0])
                self._json(403, {"error": "bad signature"})
                return

            event = self.headers.get("X-GitHub-Event", "")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid JSON"})
                return

            if event == "ping":
                self._json(200, {"ok": True, "event": "ping"})
                return

            name = payload.get("package", {}).get("name", "")
            action = payload.get("action", "")
            if event != "package" or name != PACKAGE or action != "published":
                log(f"ignored: event={event} package={name} action={action}")
                self._json(200, {"ignored": True})
                return

            threading.Thread(target=deploy, args=(dry_run,), daemon=True).start()
            self._json(202, {"deploying": True})

        def log_message(self, fmt, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("DEMIGOD_PORT", "8090")),
        help="local listener port (funnel forwards here)",
    )
    parser.add_argument(
        "--no-funnel", action="store_true", help="skip Tailscale Funnel setup"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="log deploy steps instead of running them",
    )
    args = parser.parse_args()

    secret = load_secret()
    log(f"secret loaded ({len(secret)} bytes)")

    if not args.no_funnel:
        setup_funnel(args.port)

    if args.dry_run:
        log("dry-run mode: deploy steps will only be logged")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(secret, args.dry_run))
    log(f"listening on 127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
