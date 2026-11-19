#!/usr/bin/env bash
# ONE-TIME ADMINISTRATOR ACTION. Defaults to read/write for user's media.
set -euo pipefail
if [[ $EUID -ne 0 ]]; then
  echo "This installer needs sudo. No changes were made." >&2
  exit 77
fi
MODE="${1:-rw}"
if [[ "$MODE" != "rw" && "$MODE" != "ro" || $# -gt 1 ]]; then
  echo "Usage: sudo bash $0 [rw|ro]" >&2
  exit 64
fi
TARGET=/mnt/family-usb
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
SCRIPT="$SCRIPT_DIR/family_usb_manager.py"
LIBEXEC=/usr/local/libexec/rs-family-usb-manager.py
UNIT=/etc/systemd/system/rs-family-usb-manager.service
MODE_FILE=/etc/default/rs-family-usb
BACKUP=/etc/fstab.rs-family-usb-original
[[ -f "$SCRIPT" && -d "$TARGET" && ! -L "$TARGET" ]] || { echo "Missing or untrusted source"; exit 1; }
if [[ -e "$UNIT" || -e "$LIBEXEC" || -e "$MODE_FILE" ]]; then
  echo "Manager is already installed; refusing to overwrite." >&2
  exit 2
fi
if [[ -e "$BACKUP" ]]; then
  echo "An existing fstab backup is present; review before proceeding." >&2
  exit 2
fi
# Do not disturb current mounted files; only disable the generated UUID rule
# for future boots and insertion of a DIFFERENT USB stick.
cp -p /etc/fstab "$BACKUP"
chmod 600 "$BACKUP"
installed=0
rollback_on_failure() {
  if [[ $installed -eq 0 ]]; then
    echo "USB manager installation incomplete, restoring original fstab" >&2
    cp "$BACKUP" /etc/fstab
    systemctl disable --now rs-family-usb-manager.service >/dev/null 2>&1 || true
    rm -f "$UNIT" "$LIBEXEC" "$MODE_FILE"
    systemctl daemon-reload || true
  fi
}
trap rollback_on_failure EXIT
python3 - /etc/fstab <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
lines=p.read_text().splitlines(keepends=True)
hits=[i for i,s in enumerate(lines) if s.strip() and not s.lstrip().startswith('#') and
      len(s.split())>=2 and s.split()[1]=='/mnt/family-usb']
if len(hits)!=1:
    raise SystemExit('Expected exactly one current USB mount entry; fstab unchanged')
n=hits[0]
lines[n]='# RS family USB auto-manager replaced the old UUID-specific entry\n# '+lines[n]
p.write_text(''.join(lines))
PY
install -D -m 0755 -o root -g root "$SCRIPT" "$LIBEXEC"
printf 'RS_FAMILY_USB_MODE=%s\n' "$MODE" > "$MODE_FILE"
chown root:root "$MODE_FILE"
chmod 0644 "$MODE_FILE"
cat > "$UNIT" <<'EOF'
[Unit]
Description=RS Family USB removable media manager (configurable RO/RW)
After=local-fs.target
ConditionPathIsDirectory=/mnt/family-usb
[Service]
Type=simple
EnvironmentFile=/etc/default/rs-family-usb
ExecStart=/usr/bin/python3 /usr/local/libexec/rs-family-usb-manager.py
Restart=always
RestartSec=10
UMask=0077
# Do not set PrivateTmp/PrivateMounts here: mount changes must be
# visible to the rest of the Pi, not only to this service.
[Install]
WantedBy=multi-user.target
EOF
chmod 644 "$UNIT"
systemctl daemon-reload
systemctl enable --now rs-family-usb-manager.service
if ! systemctl is-active --quiet rs-family-usb-manager.service; then
  echo "Service is not active; restoring original configuration" >&2
  exit 1
fi
installed=1
trap - EXIT
echo "Hot-swap manager installed. Selected mount mode: $MODE"
echo "Original fstab is backed up at $BACKUP"
echo "To switch mode: sudo bash $SCRIPT_DIR/set_family_usb_mode.sh rw|ro"
echo "Rollback: sudo systemctl disable --now rs-family-usb-manager.service;"
echo "          sudo cp $BACKUP /etc/fstab; sudo systemctl daemon-reload"
