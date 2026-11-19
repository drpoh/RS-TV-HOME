#!/usr/bin/env bash
# Fix an already-installed USB manager that remounted within PrivateTmp namespace.
# One-time administrator operation. Never writes any files on the USB drive.
set -euo pipefail
umask 077
if [[ $EUID -ne 0 ]]; then
  echo 'Root access is required; nothing changed.' >&2
  exit 77
fi
UNIT=/etc/systemd/system/rs-family-usb-manager.service
MODE_FILE=/etc/default/rs-family-usb
if [[ ! -f "$UNIT" || -L "$UNIT" || ! -f "$MODE_FILE" || -L "$MODE_FILE" ]]; then
  echo 'Expected installed USB manager and config not found; nothing changed.' >&2
  exit 1
fi
if ! grep -Fxq 'ExecStart=/usr/bin/python3 /usr/local/libexec/rs-family-usb-manager.py' "$UNIT" ||
   ! grep -Fxq 'PrivateTmp=true' "$UNIT"; then
  echo 'Not the known affected unit; refusing to modify it.' >&2
  exit 1
fi
MODE="$(sed -n 's/^RS_FAMILY_USB_MODE=//p' "$MODE_FILE")"
if [[ "$MODE" != 'rw' && "$MODE" != 'ro' ]]; then
  echo 'Invalid or missing USB mount mode; refusing to modify it.' >&2
  exit 1
fi
BACKUP="$(mktemp /etc/systemd/system/.rs-family-usb-unit.XXXXXXXX)"
cp -p "$UNIT" "$BACKUP"
committed=0
restore_on_failure() {
  if [[ $committed -ne 1 ]]; then
    echo 'USB namespace repair failed; restoring original service configuration.' >&2
    cp -p "$BACKUP" "$UNIT"
    systemctl daemon-reload || true
    systemctl restart rs-family-usb-manager.service || true
  fi
  rm -f "$BACKUP"
}
trap restore_on_failure EXIT
sed -i '/^PrivateTmp=true$/d' "$UNIT"
systemctl daemon-reload
systemctl restart rs-family-usb-manager.service
# The service checks a mounted drive every 10 seconds.
for attempt in {1..12}; do
  if ! systemctl is-active --quiet rs-family-usb-manager.service; then
    echo 'Manager is no longer active.' >&2
    exit 1
  fi
  CURRENT="$(findmnt -rn -M /mnt/family-usb -o OPTIONS 2>/dev/null || true)"
  if [[ ",$CURRENT," == *",$MODE,"* ]]; then
    committed=1
    echo "SUCCESS: System USB mount is now $MODE."
    break
  fi
  sleep 2
done
if [[ $committed -ne 1 ]]; then
  echo "USB mode $MODE not visible to host mount namespace." >&2
  exit 1
fi
echo 'Manager remains running; original fstab backup untouched.'
