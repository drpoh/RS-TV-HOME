#!/usr/bin/env bash
# Restore pre-hotplug fstab. Requires explicit administrator invocation.
set -euo pipefail
if [[ $EUID -ne 0 ]]; then
  echo "This rollback requires sudo. No changes were made." >&2
  exit 77
fi
BACKUP=/etc/fstab.rs-family-usb-original
[[ -s "$BACKUP" && ! -L "$BACKUP" ]] || {
  echo "Missing or unsafe fstab backup. No changes were made." >&2
  exit 1
}
systemctl disable --now rs-family-usb-manager.service >/dev/null 2>&1 || true
cp -p "$BACKUP" /etc/fstab
rm -f /etc/systemd/system/rs-family-usb-manager.service
rm -f /usr/local/libexec/rs-family-usb-manager.py
systemctl daemon-reload
echo "Original fstab restored. USB hot-swap manager disabled."
echo "The original USB must be present to use the old UUID-specific mount."
