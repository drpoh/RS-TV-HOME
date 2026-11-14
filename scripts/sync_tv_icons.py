#!/usr/bin/env python3
"""Fetch launcher icons over the already paired TV's local connection only."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
APPS = {
    "es.ottplayer.widget": "ott",
    "youtube.leanback.v4": "youtube",
    "com.rs.familyframe": "family",
    "com.webos.app.browser": "browser",
    "com.webos.app.miracast": "cast",
}
LIMIT = 2 * 1024 * 1024
PNG_HEADER = bytes.fromhex("89504e470d0a1a0a")

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def valid_url(url, host):
    try:
        p = urllib.parse.urlsplit(url)
        return p.scheme in ("http", "https") and p.hostname == host and p.username is None and p.password is None
    except (TypeError, ValueError):
        return False

def private_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise ValueError("Unsafe local config permissions")
        return json.load(f)

def sync(host, store):
    from pywebostv.connection import WebOSClient
    from pywebostv.controls import ApplicationControl
    # Never create or save a new pairing from this read-only script.
    if not store.get("client_key"):
        raise ValueError("Existing TV pairing required")
    client = WebOSClient(host)
    try:
        client.connect()
        for state in client.register(store, timeout=12):
            if state == client.PROMPTED:
                raise RuntimeError("Existing pairing rejected")
        control = ApplicationControl(client)
        # Legacy firmware may return broken listApps icon URLs; prefer launch points.
        try:
            response = control.request("ssap://com.webos.applicationManager/listLaunchPoints", {}, block=True, timeout=8)
            points = (response.get("payload") or {}).get("launchPoints") or []
        except Exception:
            points = []
        apps = list(points)
        known = {x.get("id") for x in points}
        apps.extend(a.data for a in control.list_apps(timeout=8) if a.data.get("id") not in known)
    finally:
        client.close()
    out = ROOT / ".local/tv-icons"
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    if out.is_symlink():
        raise ValueError("Unsafe icon directory")
    out.chmod(0o700)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    count = 0
    for data in apps:
        name = APPS.get(data.get("id"))
        if not name:
            continue
        for url in (data.get("largeIcon"), data.get("icon")):
            if not valid_url(url, host):
                continue
            try:
                with opener.open(url, timeout=6) as response:
                    raw = response.read(LIMIT + 1)
                if not 0 < len(raw) <= LIMIT:
                    continue
                if not (raw.startswith(PNG_HEADER) or raw.startswith(bytes.fromhex("ffd8ff"))):
                    continue
                # Normalize to a bounded PNG; strip source metadata.
                with tempfile.TemporaryDirectory(dir=out) as temp:
                    path = Path(temp) / "icon.png"
                    result = subprocess.run(
                        ["ffmpeg", "-nostdin", "-v", "error", "-max_alloc", "33554432",
                         "-threads", "1", "-i", "pipe:0", "-frames:v", "1",
                         "-vf", "scale=256:256:force_original_aspect_ratio=decrease",
                         "-map_metadata", "-1", "-threads", "1", "-y", str(path)],
                        input=raw, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=12)
                    if result.returncode or not path.is_file() or path.stat().st_size > LIMIT:
                        continue
                    path.chmod(0o600)
                    os.replace(path, out / (name + ".png"))
                count += 1
                print(name + ": OK")
                break
            except (OSError, ValueError, subprocess.TimeoutExpired):
                continue
        else:
            print(name + ": fallback")
    print("Synced", count, "of", len(APPS), "launcher icons")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--registration", required=True, type=Path)
    args = p.parse_args()
    os.umask(0o077)
    try:
        cfg = private_json(ROOT / ".local/config.json")
        host = str(ipaddress.IPv4Address(cfg["TV_HOST"]))
        sync(host, private_json(args.registration))
    except Exception as e:
        # Never print network identifiers, local paths, or pairing contents.
        print("Icon sync failed:", type(e).__name__)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
