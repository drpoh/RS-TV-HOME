#!/usr/bin/env bash
# Administrator-only switch between writable and read-only USB mounting.
set -euo pipefail
MODE="${1:-}"
if [[ "$MODE" != "rw" && "$MODE" != "ro" || $# -ne 1 ]]; then
  echo "Usage: sudo bash $0 rw|ro" >&2
  exit 64
fi
if [[ $EUID -ne 0 ]]; then
  echo "Root is required to change the USB mount mode." >&2
  exit 77
fi
CONFIG=/etc/default/rs-family-usb
SERVICE=rs-family-usb-manager.service
if [[ ! -f "$CONFIG" || -L "$CONFIG" ]] || ! systemctl cat "$SERVICE" >/dev/null 2>&1; then
  echo "USB manager is not installed; run install_family_usb_hotplug.sh first." >&2
  exit 1
fi
PREVIOUS="$(cat "$CONFIG")"
TEMP="$(mktemp /etc/default/.rs-family-usb-XXXXXXXX)"
trap 'rm -f "$TEMP"' EXIT
printf 'RS_FAMILY_USB_MODE=%s\n' "$MODE" > "$TEMP"
chown root:root "$TEMP"
chmod 0644 "$TEMP"
mv -f "$TEMP" "$CONFIG"
trap - EXIT
restore_previous() {
  printf '%s\n' "$PREVIOUS" > "$CONFIG"
  systemctl restart "$SERVICE" || true
}
if ! systemctl restart "$SERVICE"; then
  restore_previous
  echo "Mode change failed; prior setting restored." >&2
  exit 1
fi
# Confirm the requested mode if a USB device is already present. When no
# device is inserted, the configured mode applies on the next insertion.
if findmnt -rn -M /mnt/family-usb >/dev/null 2>&1; then
  matched=0
  for _ in $(seq 1 18); do
    current="$(findmnt -rn -M /mnt/family-usb -o OPTIONS || true)"
    case ",$current," in
      *,"$MODE",*) matched=1; break ;;
    esac
    sleep 1
  done
  if [[ $matched -ne 1 ]]; then
    restore_previous
    echo "USB could not switch to $MODE (busy or write-protected). Restored previous setting." >&2
    exit 1
  fi
fi
echo "USB mount mode set to $MODE. Check: findmnt -n -T /mnt/family-usb -o OPTIONS"
