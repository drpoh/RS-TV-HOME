#!/usr/bin/env bash
# Safely detach an RW/RO flash drive before unplugging it.
# Stops automounting so the mount manager cannot immediately reconnect.
set -euo pipefail
if [[ $EUID -ne 0 ]]; then
  echo "Use sudo to safely eject the USB drive." >&2
  exit 77
fi
SERVICE=rs-family-usb-manager.service
TARGET=/mnt/family-usb
if ! systemctl cat "$SERVICE" >/dev/null 2>&1; then
  echo "USB manager is not installed." >&2
  exit 1
fi
systemctl stop "$SERVICE"
sync
if findmnt -rn -M "$TARGET" >/dev/null; then
  # Never lazy unmount a writable device; report busy instead of losing writes.
  if ! umount "$TARGET"; then
    echo "USB is busy; close processes using files on it, then rerun this command." >&2
    echo "USB manager remains stopped to prevent an immediate remount." >&2
    exit 1
  fi
fi
sync
echo "USB safely unmounted. You can remove the drive."
echo "After inserting a replacement: sudo systemctl start $SERVICE"
