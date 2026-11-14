#!/usr/bin/env python3
"""Materialize local config into ignored build output; does not deploy."""
from pathlib import Path
import json, re, shutil, sys
root = Path(__file__).resolve().parents[1]
if len(sys.argv) != 2 or sys.argv[1] not in ("stable", "preview", "family-frame"):
    raise SystemExit("Usage: materialize.py stable|preview|family-frame")
version = sys.argv[1]
cfg = json.loads((root / ".local/config.json").read_text())
expected = json.loads((root / "config.example.json").read_text())
if set(cfg) != set(expected):
    raise SystemExit("Local config keys do not match example")
for k, v in cfg.items():
    if not isinstance(v, str) or not v or v in ("REPLACE_ME", "configure-locally") or any(c in v for c in ("'", chr(34), chr(92), chr(10), chr(13))):
        raise SystemExit("Invalid local setting: " + k)
if not re.fullmatch("[a-f0-9]{64}", cfg["ACTION_KEY"]):
    raise SystemExit("Invalid action key")
out = root / "dist" / version
out.mkdir(parents=True, exist_ok=True, mode=0o700)
out.chmod(0o700)
parts = [(root / "apps" / version, out / "app")]
if version == "family-frame":
    parts.append((root / "services/family-frame", out / "service"))
else:
    parts.append((root / "ha-bridge", out / "ha-bridge"))
for src, dest in parts:
    shutil.copytree(src, dest, dirs_exist_ok=True)
    for file in dest.rglob("*"):
        if file.suffix not in (".js", ".mjs", ".html", ".json", ".css", ".svg", ".py"):
            continue
        s = file.read_text()
        for k, v in cfg.items():
            s = s.replace("__RS_" + k + "__", v)
        if re.search(r"__RS_[A-Z_]+__", s):
            raise SystemExit("Unresolved placeholder: " + file.name)
        file.write_text(s)
if version != "family-frame":
    (out / "ha-bridge" / "scene-key").write_text(cfg["ACTION_KEY"] + chr(10))
    (out / "ha-bridge" / "scene-key").chmod(0o600)
print("Build files prepared for", version)
