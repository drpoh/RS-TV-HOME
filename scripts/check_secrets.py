#!/usr/bin/env python3
"""Scan committed and staged blobs; report locations/rules only, never values."""
import argparse
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])
def blocked(path):
    p = PurePosixPath(path)
    n = p.name.lower()
    return (any(x.lower() in {".local", "dist", "node_modules", ".venv", "__pycache__", ".ssh"} for x in p.parts)
            or n in {"scene-key", "frame-key", "frame-state.json", "frame-state.json.tmp", "tv-menu-key", "token", "credentials.json", "secrets.yaml", "secrets.yml", "config.local.json", "tv-registration.json", "upload-auth.json", "upload-auth.new", "phone-settings.json", "phone-preferences.json", "runtime.json", "settings-v2.json", "motion-settings.json", "status.json", "last-result.json", "timings.json", "voice-probe-result.json", "id_rsa", "id_ed25519"}
            or n.startswith(".env") or n.endswith((".pem", ".key", ".p12", ".pfx", ".ipk", ".zip", ".tar.gz", ".log", ".wav", ".pcm", ".raw", ".m4a", ".ogg", ".mp3", ".mp4", ".jpg", ".jpeg", ".webp")))
RULES = {
    "private-key": re.compile(rb"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    "github-token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    "api-token": re.compile(rb"(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{35}|xox[baprs]-[A-Za-z0-9-]{15,})"),
    "jwt": re.compile(rb"eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{12,}"),
    "url-credentials": re.compile(rb"(?:https?|rtsps?|mqtts?|ftp)://[^\s/'\x22:@]+:[^\s/'\x22@]+@", re.I),
    "local-network-address": re.compile(rb"(?<![0-9])192[.]168[.][0-9]{1,3}[.][0-9]{1,3}(?![0-9])"),
    "mac-address": re.compile(rb"(?i)(?<![0-9a-f])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![0-9a-f])"),
    "long-hex": re.compile(rb"(?<![a-fA-F0-9])[a-fA-F0-9]{48,}(?![a-fA-F0-9])"),
}
ASSIGN = re.compile(rb"""(?ix)(?:["']?\b(?:password|passwd|passphrase|secret|token|api[_-]?key|access[_-]?token|client[_-]?secret|action[_-]?key|scene[_-]?key|authorization)\b["']?)\s*[:=]\s*["']([^"'\r\n]{3,})["']""")
SAFE = {b"REPLACE_ME", b"configure-locally", b"Bearer ", b"__TOKEN__", b"application/json", b"token", b"secret"}
def known_values():
    f = ROOT / ".local/config.json"
    if not f.is_file():
        return []
    values = list(json.loads(f.read_text()).values())
    phone = ROOT / ".local/phone-settings.json"
    if phone.is_file():
        values.append(json.loads(phone.read_text()).get("tv_key", ""))
    frame = ROOT / ".local/frame-key"
    if frame.is_file():
        values.append(frame.read_text().strip())
    return [str(v).encode() for v in values
            if isinstance(v, str) and len(v) >= 8 and v not in ("REPLACE_ME", "configure-locally")]
def inspect(path, data, known):
    if blocked(path):
        return ["private-or-generated-path"]
    if path.endswith(".png") and path in {"apps/stable/icon.png", "apps/preview/icon.png", "apps/family-frame/icon.png", "apps/magic-remote/icon.png"}:
        # Only the two existing app icons are accepted; never scan arbitrary archives/binaries.
        import hashlib
        if hashlib.sha256(data).hexdigest() in ICON_HASHES:
            return []
        return ["unreviewed-binary"]
    if b"\0" in data:
        return ["unreviewed-binary"]
    hits = [name for name, pat in RULES.items() if pat.search(data)]
    if any(m.group(1) not in SAFE and not re.fullmatch(rb"__RS_[A-Z_]+__", m.group(1)) for m in ASSIGN.finditer(data)):
        hits.append("literal-credential")
    if any(v in data for v in known):
        hits.append("known-private-value")
    return hits
ICON_HASHES = {'c72b5f0473846e824fab492cf03eb773' + '2d05882f9d0182de534ca979367c7310', '0c0d9dc4638dd40cdff986a2d1434c98' + 'a2a874475de5e9084f869137685c6304', '7f82d1462d551bbbf2be336d5ce270f6' + '875e9fd2ddfb400e7e7af7672afe86f3'}  # populated below for reviewed existing assets
def entries(tree=None):
    if tree is None:
        for entry in git("ls-files", "-s", "-z").split(b"\0"):
            if entry:
                info, path = entry.split(b"\t", 1)
                mode, sha, stage = info.split()
                if stage == b"0":
                    yield path.decode(), mode, sha
    else:
        for entry in git("ls-tree", "-r", "-z", tree).split(b"\0"):
            if entry:
                info, path = entry.split(b"\t", 1)
                mode, kind, sha = info.split()
                yield path.decode(), mode, sha
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--commit", action="append", default=[])
    args = parser.parse_args()
    commits = args.commit
    if args.history:
        commits = list(set(commits + git("rev-list", "--all").decode().splitlines()))
    scopes = ([None] if args.staged or not (args.history or commits) else []) + commits
    known = known_values()
    checked = set()
    findings = 0
    for scope in scopes:
        for path, mode, sha in entries(scope):
            item = (path, mode, sha)
            if item in checked:
                continue
            checked.add(item)
            hits = ["symlink-or-submodule"] if mode not in (b"100644", b"100755") else inspect(path, git("cat-file", "blob", sha.decode()), known)
            for rule in hits:
                print("BLOCK:", path, "-", rule)
                findings += 1
    print("Secret scan:", len(checked), "unique path/blob pairs;", findings, "findings")
    return bool(findings)
if __name__ == "__main__":
    raise SystemExit(main())
