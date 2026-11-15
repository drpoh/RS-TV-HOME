#!/usr/bin/env python3
"""Materialize local config into ignored build output; does not deploy."""
from pathlib import Path
import json, re, shutil, sys, os, secrets
root = Path(__file__).resolve().parents[1]
if len(sys.argv) != 2 or sys.argv[1] not in ("stable", "preview", "family-frame", "magic-remote"):
    raise SystemExit("Usage: materialize.py stable|preview|family-frame|magic-remote")
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
elif version == "magic-remote":
    parts.append((root / "services/magic-remote", out / "service"))
else:
    parts.append((root / "ha-bridge", out / "ha-bridge"))
if version in ("stable", "preview"):
    local = root / ".local"
    local.chmod(0o700)
    auth = local / "phone-settings.json"
    if not auth.exists():
        import ipaddress
        network = str(ipaddress.ip_interface(cfg["BRIDGE_HOST"] + "/24").network)
        private = {"host": cfg["BRIDGE_HOST"], "tv": cfg["TV_HOST"], "network": network,
                   "tv_key": secrets.token_hex(32), "phone_pin": str(secrets.randbelow(100000000)).zfill(8),
                   "state_path": str(local / "phone-preferences.json")}
        fd = os.open(auth, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(private, f)
    if auth.is_symlink() or auth.stat().st_mode & 0o077:
        raise SystemExit("Unsafe phone settings file")
    private = json.loads(auth.read_text())
    if not re.fullmatch("[a-f0-9]{64}", private["tv_key"]) or not re.fullmatch("[0-9]{8}", private["phone_pin"]):
        raise SystemExit("Invalid local phone configuration")
    cfg["PHONE_TV_KEY"] = private["tv_key"]
    parts.append((root / "services/phone-settings", out / "phone-settings"))
if version == "family-frame":
    keyfile = root / ".local/frame-key"
    if not keyfile.exists():
        fd = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_hex(32))
    if keyfile.is_symlink() or keyfile.stat().st_mode & 0o077:
        raise SystemExit("Unsafe frame key")
    key = keyfile.read_text().strip()
    if not re.fullmatch("[a-f0-9]{64}", key):
        raise SystemExit("Invalid frame key")
    cfg["FRAME_KEY"] = key
for src, dest in parts:
    shutil.copytree(src, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "runtime.json"))
    for file in dest.rglob("*"):
        if file.suffix not in (".js", ".mjs", ".html", ".json", ".css", ".svg", ".py", ".rules"):
            continue
        s = file.read_text()
        for k, v in cfg.items():
            s = s.replace("__RS_" + k + "__", v)
        if re.search(r"__RS_[A-Z_]+__", s):
            raise SystemExit("Unresolved placeholder: " + file.name)
        file.write_text(s)
if version in ("stable", "preview"):
    runtime = out / "phone-settings" / "runtime.json"
    fd = os.open(runtime, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(private, f)
    runtime.chmod(0o600)
if version in ("stable", "preview"):
    (out / "ha-bridge" / "scene-key").write_text(cfg["ACTION_KEY"] + chr(10))
    (out / "ha-bridge" / "scene-key").chmod(0o600)
    lighting = root / ".local" / "lighting.json"
    dest_lighting = out / "ha-bridge" / "lighting.json"
    if lighting.exists():
        if lighting.is_symlink() or lighting.stat().st_mode & 0o077:
            raise SystemExit("Unsafe lighting configuration")
        shutil.copyfile(lighting, dest_lighting)
        dest_lighting.chmod(0o600)
    elif dest_lighting.exists():
        dest_lighting.unlink()

if version in ("stable", "preview"):
    # Private, optional assets fetched from this user's TV; never copy into source.
    icon_dir = out / "app" / "tv-icons"
    if icon_dir.exists():
        shutil.rmtree(icon_dir)
    rules = []
    for name in ("ott", "youtube", "family", "browser", "cast"):
        original = root / ".local" / "tv-icons" / (name + ".png")
        if original.is_symlink() or not original.is_file() or original.stat().st_size > 2*1024*1024:
            continue
        if not original.read_bytes().startswith(bytes.fromhex("89504e470d0a1a0a")):
            continue
        icon_dir.mkdir(mode=0o755, exist_ok=True)
        target = icon_dir / original.name
        shutil.copyfile(original, target)
        target.chmod(0o644)
        rules.append("#tiles .tile." + name + " .mark{background-image:url(tv-icons/" + name + ".png)!important}")
    page = out / "app" / "index.html"
    if rules:
        page.write_text(page.read_text().replace("</style>", chr(10).join(rules) + chr(10) + "</style>", 1))
    print("Optional local TV icons:", len(rules))
if version == "magic-remote":
    (out / "service" / "tv-menu-key").write_text(cfg["REMOTE_MENU_KEY"] + chr(10))
    (out / "service" / "tv-menu-key").chmod(0o600)
print("Build files prepared for", version)
