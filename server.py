#!/usr/bin/env python3
"""Home portal server.

Serves static files from ./static and a single API endpoint:
  GET /api/devices -> JSON list of tailnet devices (name + status)

Uses the local `tailscale` CLI, so run this on a machine in your tailnet.
"""

import json
import subprocess
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

STATIC_DIR = Path(__file__).parent / "static"


def get_devices():
    out = subprocess.run(
        ["tailscale", "status", "--json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    data = json.loads(out)

    peers = list(data.get("Peer", {}).values())
    if data.get("Self"):
        peers.append(data["Self"])

    devices = []
    for p in peers:
        devices.append(
            {
                "dns": (p.get("DNSName") or "").rstrip("."),
                "ip": (p.get("TailscaleIPs") or [""])[0],
                "os": p.get("OS") or "",
                "online": bool(p.get("Online")),
            }
        )
    devices.sort(key=lambda d: d["dns"])
    return devices


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/devices":
            self._send_json(200, {"devices": get_devices()})
        else:
            super().do_GET()

    def _send_json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = HTTPServer(("", port), Handler)
    print(f"Serving on http://0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
