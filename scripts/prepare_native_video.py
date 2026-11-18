#!/usr/bin/env python3
"""Prepare one private MP4 display copy for native LG SmartShare.

Original media stays on the USB read-only. Output is only under the Pi cache.
Metadata mode is fast but requires visual verification that SmartShare honors
the MP4 display matrix. Pixel mode is slower but normalizes source rotation
and then adds an additional clockwise quarter-turn.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / ".cache" / "rs-family-frame" / "smartshare-video"


def probe(path):
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=30, check=True,
    )
    result = json.loads(proc.stdout)
    stream = result["streams"][0]
    matrices = [s.get("rotation") for s in stream.get("side_data_list", [])
                if s.get("side_data_type") == "Display Matrix"]
    original_rotation = round(float(matrices[0] if matrices else 0))
    duration = float(result["format"].get("duration") or 0)
    return {
        "codec": stream["codec_name"],
        "angle": original_rotation,
        "duration": duration,
        "width": int(stream["width"]),
        "height": int(stream["height"]),
    }


def clockwise_plus_90(original):
    # ffprobe/ffmpeg display rotation is counter-clockwise in degrees.
    return (round(original) - 90 + 180) % 360 - 180


def ffmpeg(args, timeout):
    cmd = ["nice", "-n", "15", "ionice", "-c", "3",
           "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error"] + args
    subprocess.run(cmd, check=True, timeout=timeout)


def prepare(source, mode, limit_seconds=300):
    CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
    CACHE.chmod(0o700)
    source_stat = source.stat()
    info = probe(source)
    if info["duration"] <= 0:
        raise RuntimeError("Input video has no duration")
    if mode == "auto":
        mode = "metadata" if info["codec"] == "h264" else "pixels"
    if mode == "metadata" and info["codec"] != "h264":
        raise RuntimeError("Legacy LG metadata mode requires an H.264 input")
    new_angle = clockwise_plus_90(info["angle"])
    checksum = hashlib.sha256(
        (str(source.resolve()) + ":" + str(source_stat.st_size) + ":" +
         str(source_stat.st_mtime_ns) + ":" + mode + ":v1").encode()
    ).hexdigest()
    final = CACHE / (checksum + ".mp4")
    if final.is_file():
        print("CACHE_EXISTS", mode, "bytes", final.stat().st_size, flush=True)
        return final
    available = shutil.disk_usage(CACHE).free
    minimum = source_stat.st_size * (3 if mode == "pixels" else 2) + 2*1024**3
    if available < minimum:
        raise OSError("Insufficient free Pi storage for a private copy")
    first = CACHE / (checksum + ".stage1.mp4")
    second = CACHE / (checksum + ".stage2.mp4")
    try:
        t0 = time.monotonic()
        if mode == "metadata":
            ffmpeg(["-display_rotation:v:0", str(new_angle),
                    "-i", str(source), "-map", "0", "-c", "copy",
                    "-movflags", "+faststart", "-y", str(second)], 120)
        else:
            # Default autorotate applies any existing MP4 display matrix.
            # transpose=clock is an EXTRA 90 degrees clockwise after that.
            ffmpeg(["-threads", "1", "-i", str(source),
                    "-map", "0:v:0", "-map", "0:a:0?",
                    "-vf", "transpose=clock", "-c:v", "libx264",
                    "-preset", "ultrafast", "-crf", "24", "-pix_fmt", "yuv420p",
                    "-c:a", "copy", "-map_metadata", "-1",
                    "-movflags", "+faststart", "-y", str(first)], limit_seconds)
            # Some FFmpeg builds propagate the input's display matrix even
            # after transforming the decoded pixels. Clear it explicitly.
            ffmpeg(["-display_rotation:v:0", "0", "-i", str(first),
                    "-map", "0", "-c", "copy", "-movflags", "+faststart",
                    "-y", str(second)], 120)
        actual = probe(second)
        if abs(actual["duration"] - info["duration"]) > 1:
            raise RuntimeError("Output duration differs from the input")
        if actual["codec"] != "h264":
            raise RuntimeError("Output is not H.264")
        if mode == "pixels" and actual["angle"] != 0:
            raise RuntimeError("Output has unwanted rotation metadata")
        if mode == "metadata" and actual["angle"] != new_angle:
            raise RuntimeError("Output display matrix does not match target")
        second.chmod(0o600)
        second.rename(final)
        print("PREPARED", mode, "input_angle", info["angle"],
              "target_angle", new_angle, "duration_s", round(actual["duration"], 1),
              "output_dimensions", str(actual["width"]) + "x" + str(actual["height"]),
              "output_bytes", final.stat().st_size,
              "processing_seconds", round(time.monotonic() - t0, 1),
              flush=True)
        return final
    finally:
        for temp in (first, second):
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rank", type=int, default=1, help="1 = largest video on USB")
    p.add_argument("--mode", choices=("auto", "metadata", "pixels"), default="auto")
    p.add_argument("--run", action="store_true", help="Create private MP4 copy")
    p.add_argument("--timeout", type=int, default=300)
    args = p.parse_args()
    config = json.loads((PROJECT / ".local" / "config.json").read_text())
    usb = Path(config["FAMILY_USB_PATH"])
    videos = sorted((f for f in usb.iterdir() if f.is_file() and not f.is_symlink()
                     and f.suffix.lower() == ".mp4"),
                    key=lambda f: (-f.stat().st_size, f.name))
    if not (1 <= args.rank <= len(videos)):
        p.error("Rank outside available MP4 videos")
    source = videos[args.rank-1]
    stats = probe(source)
    target = clockwise_plus_90(stats["angle"])
    print("SOURCE", "rank", args.rank, "codec", stats["codec"],
          "duration_s", round(stats["duration"], 1),
          "angle_before", stats["angle"], "angle_after", target,
          "requested_mode", args.mode, flush=True)
    if args.run:
        prepare(source, args.mode, args.timeout)
    else:
        print("DRY_RUN: add --run to prepare a cached copy", flush=True)


if __name__ == "__main__":
    main()
