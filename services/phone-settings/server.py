"""Local-only launcher preferences. No device control or Home Assistant credentials."""
import hmac
import ipaddress
import json
import os
from pathlib import Path
import secrets
import stat
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APPS = ("es.ottplayer.widget", "youtube.leanback.v4", "coffee_power",
        "com.rs.familyframe", "com.webos.app.browser", "com.webos.app.miracast")
THEMES = ("blue", "violet", "forest", "graphite")
WIDGETS = ("outdoor", "indoor", "sauna", "price", "camera", "chart")
ROOT = Path(__file__).resolve().parent
PORT = 8790
LOCK = threading.RLock()
ATTEMPTS = {}
# Private runtime file is provisioned locally by materialize.py.
def load_private(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as f:
        st = os.fstat(f.fileno())
        if st.st_uid != os.getuid() or st.st_mode & 0o077 or not stat.S_ISREG(st.st_mode):
            raise ValueError("Unsafe local file")
        return json.load(f)

def normalize(p):
    if not isinstance(p, dict) or set(p) != {"theme", "order", "hidden"}:
        raise ValueError("Invalid preferences")
    if p["theme"] not in THEMES or not isinstance(p["order"], list) or not isinstance(p["hidden"], list):
        raise ValueError("Invalid preferences")
    if any(not isinstance(x, str) or x not in APPS for x in p["order"]) or len(set(p["order"])) != len(p["order"]):
        raise ValueError("Invalid app order")
    if any(not isinstance(x, str) or x not in WIDGETS for x in p["hidden"]) or len(set(p["hidden"])) != len(p["hidden"]):
        raise ValueError("Invalid widgets")
    return {"theme": p["theme"], "order": p["order"] + [x for x in APPS if x not in p["order"]],
            "hidden": p["hidden"]}

class Store:
    def __init__(self, path):
        self.path = path
        self.data = load_private(path) if path.exists() else {"revision": 0, "preferences": None}
    def write(self, preferences, revision):
        with LOCK:
            if type(revision) is not int or revision != self.data["revision"]:
                return False
            value = {"revision": revision + 1, "preferences": normalize(preferences)}
            temp = self.path.with_name(self.path.name + ".tmp")
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump(value, f)
            os.replace(temp, self.path)
            self.data = value
            return True

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def setup(self):
        super().setup()
        self.connection.settimeout(6)
    def reply(self, code, value, typ="application/json", tv=False):
        b = json.dumps(value).encode() if typ == "application/json" else value
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
        if tv:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b)
    def permitted(self):
        return (ipaddress.ip_address(self.client_address[0]) in self.server.network
                and self.headers.get("Host") == self.server.host_header)
    def do_GET(self):
        if not self.permitted():
            return self.reply(403, {})
        if self.path != "/":
            return self.reply(404, {})
        self.reply(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
    def do_POST(self):
        tv = self.client_address[0] == self.server.tv and self.path == "/tv"
        if not self.permitted():
            return self.reply(403, {})
        if self.path not in ("/tv", "/phone") or (self.path == "/tv" and not tv):
            return self.reply(403, {})
        origin = self.headers.get("Origin")
        if not tv and origin and origin != "http://" + self.server.host_header:
            return self.reply(403, {})
        if self.headers.get("Transfer-Encoding") or not self.headers.get("Content-Type", "").startswith("text/plain"):
            return self.reply(400, {}, tv=tv)
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= 8192:
                raise ValueError()
            body = json.loads(self.rfile.read(n))
            if not isinstance(body, dict):
                raise ValueError()
        except (ValueError, OSError):
            return self.reply(400, {}, tv=tv)
        key = body.get("key")
        if not isinstance(key, str) or not key.isascii() or len(key) > 128:
            return self.reply(403, {}, tv=tv)
        # Rate-limit guesses across the entire LAN, not just one client address.
        with LOCK:
            now = time.monotonic()
            slot = "tv" if tv else "phone"
            bad = [t for t in ATTEMPTS.get(slot, []) if now - t < 300]
            if len(bad) >= 5:
                return self.reply(429, {}, tv=tv)
            expected = self.server.config["tv_key" if tv else "phone_pin"]
            if not hmac.compare_digest(key, expected):
                ATTEMPTS[slot] = bad + [now]
                return self.reply(403, {}, tv=tv)
        op = body.get("op")
        if op == "pair" and tv:
            return self.reply(200, {"pin": self.server.config["phone_pin"]}, tv=True)
        if op not in ("read", "write"):
            return self.reply(400, {}, tv=tv)
        with LOCK:
            if op == "write":
                try:
                    ok = self.server.store.write(body.get("preferences"), body.get("revision"))
                except ValueError:
                    return self.reply(400, {}, tv=tv)
                if not ok:
                    return self.reply(409, self.server.store.data, tv=tv)
            self.reply(200, self.server.store.data, tv=tv)

def main():
    os.umask(0o077)
    cfg = load_private(ROOT / "runtime.json")
    host = str(ipaddress.IPv4Address(cfg["host"]))
    http = ThreadingHTTPServer((host, PORT), Handler)
    http.network = ipaddress.ip_network(cfg["network"])
    http.host_header = host + ":" + str(PORT)
    http.tv = cfg["tv"]
    http.config = cfg
    http.store = Store(Path(cfg["state_path"]))
    http.serve_forever()

if __name__ == "__main__":
    main()
