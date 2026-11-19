# LG MR22 cursor recovery guard on Raspberry Pi 3

## Observed November 19, 2026

Repeated failures in the on-board Pi 3 Bluetooth HCI UART can look connected in
BlueZ and RS Magic Remote but stop delivering new HID reports and cursor moves.
The kernel shows many hci0 "Received unexpected HCI Event 0x00" / "Frame
reassembly failed (-84)" messages at the same moment. Restarting only the
Python remote bridge is insufficient. Cycling the Pi's Bluetooth adapter
while preserving the pairing and reconnecting the trusted MR22 restored
traffic on two separate incidents that day.

This class of Raspberry Pi 3 onboard Bluetooth fault has been reported by
Raspberry Pi Linux maintainers. Exact root cause for this particular Pi is
not yet established. No firmware or OS changes were made.

## Conservative automatic recovery

scripts/mr22_bt_guard.py is checked by a user-level systemd timer:

- Reuses the existing read-only RS Magic Remote status API.
- Checks dmesg for at least six hci0 frame-reassembly/unknown HCI-event
  messages within the preceding 110 seconds (boot-relative timestamps).
- Only then checks that the TV, HID and pointer mode are all active while the
  number of HID reports remains unchanged across an 8-second probe.
- Does not act on an idle or asleep remote without a fresh HCI fault burst.
- Permits at most one attempted recovery per boot per 30 minutes.
- Uses a local lock, checks for other connected BT devices, preserves pairing,
  only stops/restarts RS Magic Remote and cycles Pi Bluetooth.
- Does not reboot Pi or LG; does not alter photos, videos or settings.
- All state files are stored privately under ~/.cache/rs-family-frame/.

Systemd unit files are stored under systemd/. They can be installed in the
normal user unit directory (no sudo required). They are not systemwide units.

Manual read-only check:

    python3 scripts/mr22_bt_guard.py
    python3 scripts/recover_magic_remote.py --check

Manual recovery, if necessary and another Bluetooth device is not in use:

    python3 scripts/recover_magic_remote.py --recover

Status:

    systemctl --user status rs-mr22-guard.timer
    systemctl --user list-timers --all | grep rs-mr22-guard

Turn automatic monitoring off (stops future resets but does not stop the
working remote bridge):

    systemctl --user disable --now rs-mr22-guard.timer

User-level installation:

    mkdir -p ~/.config/systemd/user
    cp systemd/rs-mr22-guard.{service,timer} ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now rs-mr22-guard.timer

To remove after disabling, remove these two user units and daemon-reload.

For longer-term repair consider avoiding the Pi 3 onboard UART Bluetooth,
using a supported USB adapter or migrating this peripheral to newer hardware.
No automatic apt, firmware or kernel changes are part of this recovery.
