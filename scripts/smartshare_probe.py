#!/usr/bin/env python3
"""One-off, read-only USB video playback test on a legacy LG SmartShare TV.

Only the two TV applications are switched. The existing family-frame server
continues to serve its previously prepared private fast-start cache files.
The photo collection, metadata, configuration, and TV app packages are untouched.
"""
import argparse
import hashlib
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".local" / "config.json"
CLI = Path.home() / "lg-webos-tools/node_modules/.bin/ares-launch"


def get_renderer(host):
    desc = "http://" + host + ":1856/"
    with urllib.request.urlopen(desc, timeout=5) as response:
        if response.status != 200:
            raise OSError("Renderer description failed")
        root = ET.fromstring(response.read(256000))
    service = next(
        s for s in root.findall(".//{*}service")
        if "AVTransport" in s.findtext("{*}serviceType", "")
    )
    endpoint = urllib.parse.urljoin(desc, service.findtext("{*}controlURL"))
    if urllib.parse.urlparse(endpoint).hostname != host:
        raise OSError("Unexpected AVTransport hostname")
    return endpoint, service.findtext("{*}serviceType")


def transport(endpoint, service):
    action = "GetTransportInfo"
    body = (
        '<?xml version="1.0"?><s:Envelope '
        'xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        '<s:Body><u:GetTransportInfo xmlns:u="'
        + service
        + '"><InstanceID>0</InstanceID></u:GetTransportInfo></s:Body>'
        '</s:Envelope>'
    ).encode()
    request = urllib.request.Request(
        endpoint, body,
        headers={
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPACTION": '"' + service + "#" + action + '"',
        },
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        result = ET.fromstring(response.read(16000))
    return result.findtext(".//{*}CurrentTransportState", "UNKNOWN")


def launch(application, alias, params=None):
    cmd = [str(CLI), application]
    if params is not None:
        cmd.extend(["-p", json.dumps(params, separators=(",", ":"))])
    cmd.extend(["-d", alias])
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=30, check=False
    )
    return result.returncode == 0 and "Launched application" in result.stdout


def details(file):
    raw = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=codec_name,codec_type",
            "-of", "json", str(file),
        ],
        timeout=12,
    )
    data = json.loads(raw)
    duration = float(data["format"]["duration"])
    video = next(
        (s.get("codec_name") for s in data["streams"] if s.get("codec_type") == "video"),
        None,
    )
    return duration, video


def main():
    parser = argparse.ArgumentParser(description="Test one native LG video and return to family frame.")
    parser.add_argument("--rank", type=int, default=1, help="1=largest MP4 by source size")
    parser.add_argument("--no-launch", action="store_true", help="Probe video and DLNA endpoint only")
    args = parser.parse_args()
    if args.rank < 1 or args.rank > 2000:
        parser.error("Rank must be positive and at most 2000")
    config = json.loads(CONFIG.read_text())
    usb = Path(config["FAMILY_USB_PATH"])
    files = sorted(
        (p for p in usb.iterdir() if p.is_file() and not p.is_symlink()
         and p.suffix.lower() == ".mp4"),
        key=lambda p: (-p.stat().st_size, p.name),
    )
    if args.rank > len(files):
        parser.error("Rank exceeds video count")
    source = files[args.rank - 1]
    duration, codec = details(source)
    endpoint, service = get_renderer(config["TV_HOST"])
    print("VIDEO", "rank", args.rank, "duration_s", round(duration, 1),
          "size_mb", round(source.stat().st_size / (1024**2), 1),
          "codec", codec, flush=True)
    print("DLNA_AVTRANSPORT", transport(endpoint, service), flush=True)
    if args.no_launch:
        return
    video_id = hashlib.sha256(os.fsencode(source)).hexdigest()[:24]
    url = "http://" + config["BRIDGE_HOST"] + ":8788/video/" + video_id
    payload = {"payload": [{
        "fullPath": url, "artist": "", "subtitle": "",
        "dlnaInfo": {
            "flagVal": 4096, "cleartextSize": "-1", "contentLength": "-1",
            "opVal": 1,
            "protocolInfo": (
                "http-get:*:video/mp4:DLNA.ORG_OP=01;DLNA.ORG_CI=0;"
                "DLNA.ORG_FLAGS=01700000000000000000000000000000"
            ),
            "duration": 0,
        },
        "mediaType": "VIDEO", "thumbnail": "", "deviceType": "DMR",
        "album": "", "fileName": "RS Native Playback Test",
        "lastPlayPosition": -1,
    }]}
    started = False
    reached_end = False
    first_playing = None
    launch_ok = False
    try:
        launch_ok = launch("com.webos.app.smartshare", config["TV_DEVICE_ALIAS"], payload)
        print("SMARTSHARE_LAUNCHED", launch_ok, flush=True)
        if not launch_ok:
            return
        start = time.monotonic()
        last = None
        limit = duration + 60
        while time.monotonic() - start < limit:
            try:
                current = transport(endpoint, service)
            except (OSError, ValueError, ET.ParseError):
                current = "UNKNOWN"
            if current != last:
                print("DLNA_STATE", round(time.monotonic() - start, 1),
                      current, flush=True)
                last = current
            if current == "PLAYING":
                started = True
                if first_playing is None:
                    first_playing = time.monotonic()
            if started and current == "STOPPED":
                played_time = time.monotonic() - first_playing
                reached_end = played_time >= duration * 0.75
                print("STOPPED_AFTER_PLAYBACK_SEC", round(played_time, 1),
                      "LONG_ENOUGH", reached_end, flush=True)
                break
            if not started and time.monotonic() - start > 24:
                print("START_TIMEOUT", flush=True)
                break
            time.sleep(1.5)
    finally:
        restored = launch("com.rs.familyframe", config["TV_DEVICE_ALIAS"])
        print("FRAME_RETURN", restored, flush=True)
    print("RESULT", "COMPLETED" if reached_end else
          ("INCOMPLETE_OR_UNSUPPORTED" if launch_ok else "LAUNCH_FAILED"), flush=True)


if __name__ == "__main__":
    main()
