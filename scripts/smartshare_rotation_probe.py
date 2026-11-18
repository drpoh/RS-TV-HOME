#!/usr/bin/env python3
"""Private, temporary LG SmartShare test for two 90-degree rotation strategies.

Original USB and deployed RS Family Frame files are read-only. This script
uses a one-off HTTP Range server that exposes exactly two files to the TV,
launches native SmartShare on the TV, watches AVTransport, and always restores
the frame. No permanent service, web UI change, or source-media modification.
"""
import argparse
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from smartshare_probe import get_renderer, transport, launch

PROJECT = Path(__file__).resolve().parents[1]
WORK = Path.home() / ".cache/rs-smartshare-rotation"
PORT = 8792

class SourceHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_HEAD(self):
        self.serve(False)

    def do_GET(self):
        self.serve(True)

    def serve(self, data):
        # Private local network test only; deny other LAN machines.
        if self.client_address[0] not in self.server.allowed:
            self.send_error(403)
            return
        src = self.server.routes.get(self.path)
        if src is None or not src.is_file() or src.is_symlink():
            self.send_error(404)
            return
        size = src.stat().st_size
        start, end = 0, size - 1
        hdr = self.headers.get("Range")
        if hdr:
            m = re.fullmatch(r"bytes=(\d*)-(\d*)", hdr.strip())
            if not m or not (m[1] or m[2]):
                self.send_error(416)
                return
            if m[1]:
                start = int(m[1])
                if m[2]:
                    end = min(end, int(m[2]))
            else:
                start = max(0, size - int(m[2]))
            if start >= size or start > end:
                self.send_error(416)
                return
        self.send_response(206 if hdr else 200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if hdr:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        self.server.requests += 1
        if data:
            try:
                with src.open("rb") as file:
                    file.seek(start)
                    remain = end-start+1
                    while remain:
                        block = file.read(min(remain, 64*1024))
                        if not block:
                            break
                        self.wfile.write(block)
                        remain -= len(block)
                        self.server.bytes += len(block)
            except OSError:
                pass

def native_payload(url):
    return {"payload": [{
        "fullPath": url, "artist": "", "subtitle": "",
        "dlnaInfo": {
            "flagVal": 4096, "cleartextSize": "-1", "contentLength": "-1",
            "opVal": 1,
            "protocolInfo": ("http-get:*:video/mp4:DLNA.ORG_OP=01;"
                             "DLNA.ORG_CI=0;"
                             "DLNA.ORG_FLAGS=01700000000000000000000000000000"),
            "duration": 0,
        },
        "mediaType": "VIDEO", "thumbnail": "", "deviceType": "DMR",
        "album": "", "fileName": "RS Rotation Trial",
        "lastPlayPosition": -1,
    }]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["metadata", "pixels", "hevc", "hevc-h264", "both"], default="both")
    args = parser.parse_args()
    c = json.loads((PROJECT / ".local/config.json").read_text())
    alias = c["TV_DEVICE_ALIAS"]
    routes = {
        "/meta.mp4": WORK / "rotate-meta-cw90.mp4",
        "/pixels.mp4": WORK / "rotate-pixels-cw90.mp4",
    }
    if args.mode == "hevc-h264":
        routes["/hevc-h264.mp4"] = WORK / "hevc-h264-cw90-cleared.mp4"
    if args.mode == "hevc":
        sample = json.loads((WORK / "hevc-source.json").read_text())
        source = Path(sample["source"])
        usb = Path(c["FAMILY_USB_PATH"])
        if source.parent.resolve() != usb.resolve() or source.suffix.lower() != ".mp4":
            raise SystemExit("HEVC trial must use a video from the configured USB root")
        routes["/hevc.mp4"] = source
    if any(not f.is_file() or f.is_symlink() for f in routes.values()):
        raise SystemExit("Missing prepared sample file")
    endpoint, service = get_renderer(c["TV_HOST"])
    server = ThreadingHTTPServer((c["BRIDGE_HOST"], PORT), SourceHandler)
    server.daemon_threads = True
    server.routes = routes
    server.allowed = {c["TV_HOST"], c["BRIDGE_HOST"], "127.0.0.1"}
    server.requests = server.bytes = 0
    runner = threading.Thread(target=server.serve_forever, daemon=True)
    runner.start()
    modes = (["metadata", "pixels"] if args.mode == "both" else [args.mode])
    try:
        for mode in modes:
            route = { "metadata": "/meta.mp4", "pixels": "/pixels.mp4", "hevc": "/hevc.mp4", "hevc-h264": "/hevc-h264.mp4" }[mode]
            url = f"http://{c['BRIDGE_HOST']}:{PORT}{route}"
            was_playing = False
            stopped = False
            print("TRIAL", mode, "VIDEO_SIZE_KB",
                  round(routes[route].stat().st_size / 1024), flush=True)
            requests_before = server.requests
            try:
                ok = launch("com.webos.app.smartshare", alias, native_payload(url))
                print("LAUNCH_OK", ok, flush=True)
                if not ok:
                    continue
                start = time.monotonic()
                last = None
                while time.monotonic() - start < 38:
                    try:
                        st = transport(endpoint, service)
                    except (OSError, ValueError):
                        st = "UNKNOWN"
                    if st != last:
                        print("DLNA_STATE", mode, round(time.monotonic() - start, 1), st,
                              flush=True)
                        last = st
                    if st == "PLAYING":
                        was_playing = True
                    if was_playing and st == "STOPPED":
                        stopped = True
                        break
                    if not was_playing and time.monotonic() - start > 17:
                        break
                    time.sleep(1.5)
            finally:
                restored = launch("com.rs.familyframe", alias)
                print("RETURNED_TO_FRAME", restored, flush=True)
            print("TRIAL_RESULT", mode,
                  "PLAYED_TO_STOP" if stopped and server.requests > requests_before else "NOT_CONFIRMED",
                  "NEW_REQUESTS", server.requests - requests_before,
                  "TOTAL_SENT_MB", round(server.bytes / 1048576, 2),
                  flush=True)
            time.sleep(2)
    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()
