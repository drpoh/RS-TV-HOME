# Magic Remote connection recovery

The bridge distinguishes a silent HID stream from a stalled worker. After 8 seconds without a valid report it reopens the HID descriptor. After 30 seconds of silence following valid reports, it attempts one reconnection of the existing trusted Bluetooth device. Radio recovery is limited to one attempt per silent period and a minimum two-minute cooldown; a sleeping remote can also trigger it. Pairing, key assignments and calibration are not changed.

TCP keepalive is enabled on both webOS sockets. An independent watchdog restarts a frozen worker through the existing systemd restart policy, with a longer deadline for connection setup. No claim is made that a successful TCP send proves a button was processed by the TV. Recovery causes brief interruption; physical testing is needed.

Run python3 services/magic-remote/test_recovery.py for deterministic timing-policy tests. Local logs contain generic recovery event labels only.
