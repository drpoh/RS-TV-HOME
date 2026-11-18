# Family Frame 1.2.3

Use the remote left/right for previous/next, OK for pause/resume and up/down for the playback menu. Clicking the displayed media also opens the menu. Back closes the menu (then exits the app). Opening the menu pauses playback; select Continue to resume. Photo interval is 5–120 seconds in five-second increments, videos play to completion. Choose all media, photos only, or videos only; shuffle or sequential order; optional clock. Local playback preferences persist in the TV's application storage.

Rotate either direction in 90-degree steps. Save rotation stores display orientation separately on the Pi, with no changes to original media and no video transcoding. Unsaved rotation is discarded when changing files. Delete requires confirmation and hides the item from playback; restore recovers the most recently hidden item. No original file is physically deleted. USB remains read-only.

Source contains no album content or metadata. Materialize family-frame to generate a separate local edit key, and deploy the app and server together. The authenticated edit endpoint accepts only requests from the configured TV, with an allowlisted operation and known media ID. Runtime orientation/hidden state is local-only under the user's configuration directory. Original upload service remains independent.

Run python3 services/family-frame/test_edits.py for isolated synthetic API tests. Real-TV rendering and remote operation require manual verification.

1.2.1 keeps menu nodes stable during unchanged album refreshes, uses a separate input surface above media, and restores focus on visibility and window changes. Cursor visibility is still controlled by webOS and the remote input connection.

## 1.2.3 — USB MP4 playback reliability

Most original USB MP4s had their container index (moov) beyond the first megabyte. Raspberry Pi prepares separate private copies under ~/.cache/rs-family-frame/video/ using ffmpeg stream-copy and +faststart. Video and audio are not re-encoded, and the original USB remains read-only. Cache filenames are derived from the source path, file size and modification time. Cache directory permissions are 0700 and files are 0600.

After materializing Family Frame, run the prepare_videos.py helper in the ignored dist/family-frame/service directory to prebuild the cache. The HTTP server serves optimized ready copies with normal byte-range support. For new MP4 files, one bounded background cache worker prepares copies while original playback remains available. At least 4 GiB free space must remain.

The TV client now checks actual media currentTime progress. After 8 seconds without progress, it retries the file once and seeks to the last seen position when supported. If playback freezes again, it skips the file instead of remaining stuck. Paused or hidden playback is excluded from this recovery check.

Tests: python3 services/family-frame/test_edits.py and node apps/family-frame/test-playback.cjs. They use synthetic media and never modify original USB. Some highly compressed or high-bitrate videos may still be incompatible with older TV hardware; playback on the real television requires final verification.

## 1.2.4 — Complete videos and universal video rotation

All video files play until the media element reports native `ended` (or the user explicitly selects the next item). The video no longer inherits a slideshow timeout, a 30-second startup/buffering watchdog or the 8-second playback-progress auto-skip. Network buffering displays a message but does not restart the source or advance the playlist. A fatal media error is still handled by the existing error route; unsupported/corrupt media cannot be guaranteed to play.

Every video's displayed orientation includes a permanent +90-degree clockwise baseline. Per-file saved rotation remains an additional offset: `(saved + 90) % 360`. Photos retain their existing orientation and interval. The original USB files and cached MP4 streams are not re-encoded or rotated, only the TV display is rotated. This baseline needs no new preference and therefore survives app restarts and future album refreshes.

Run `node apps/family-frame/test-playback.cjs`, which simulates long buffering, native video completion, global and per-file rotation, and unchanged photo timing. Real-TV playback and landscape/portrait visual proportions require verification on LG.

## 1.2.5 — Changing USB drives and media contents

- The album API now provides a short opaque per-item `rev` alongside the
  persistent path-based media ID. It reflects file size, modification time,
  inode, device and volume mount generation. A replaced USB drive with the
  same filenames can still change the item revision.
- The TV checks the album every 30 seconds. It keeps the current item when
  unchanged; if its revision changes, the display reloads the file. If a
  current item is removed, the player moves to a remaining valid item.
  When the USB is absent and there are no other files it shows an empty
  collection message. Reinserted media appears without rebooting the TV.
- The Pi server also scans nested folders (up to four levels), without
  following symlinks or crossing filesystem boundaries, with limits to
  avoid expensive scans on an underpowered Raspberry Pi 3.
- The USB mount at /mnt/family-usb is currently defined by a fixed UUID
  in the Pi's /etc/fstab. This is a separate OS-level limitation: another
  USB stick with a different UUID will need an auto-mount manager or admin
  reconfiguration. This app update alone does not change /etc/fstab.
- Photos/videos remain read-only; video cached copies are generated on Pi.
  Existing per-file rotation and hidden settings continue to use the
  stable path-based media ID. The native SmartShare hybrid remains disabled.

Run: node apps/family-frame/test-playback.cjs
Run: python3 services/family-frame/test_edits.py

### Optional root-level auto-mount of different USB drives

The currently active Pi mounts the existing flash at /mnt/family-usb as
read-only with a fixed filesystem UUID in /etc/fstab. This works for file edits
and re-plugging the *same* flash, but not a different drive with another UUID.
The app itself cannot mount block devices without administrator privileges.

The repository includes a **separate, not activated** mount manager:
scripts/family_usb_manager.py. It monitors attached USB block devices every
10 seconds and mounts one supported USB volume at /mnt/family-usb using
ro,nosuid,nodev,noexec. Supported filesystems: FAT, exFAT, NTFS, ext4. It
does not touch the SD-card boot/root partitions, refuses to choose between
multiple unmounted USB volumes, leaves a currently working read-only mount
alone, and avoids mounting a USB already used elsewhere.

The installer requires *one explicit terminal invocation with sudo* on Pi:

    cd ~/projects/RS-TV-HOME
    sudo bash scripts/install_family_usb_hotplug.sh

It backs up /etc/fstab to /etc/fstab.rs-family-usb-original, comments
only the previous /mnt/family-usb entry, and installs a root-owned copy of
the manager with its systemd unit. The installer attempts to restore fstab
on failure. No original USB file is modified.

To fully roll back that optional installation:

    cd ~/projects/RS-TV-HOME
    sudo bash scripts/uninstall_family_usb_hotplug.sh

This switches back to the old UUID-specific fstab entry. The actual mount
can be checked without sudo first:

    python3 scripts/family_usb_manager.py --check

These scripts were unit-tested without touching /etc/fstab:

    python3 scripts/test_family_usb_manager.py

The manager is a prepared capability, **not installed or enabled** by the
user-level remote account. It requires administrator installation and a
real unplug/replug test before full USB swap support is confirmed.

### Writable USB support (optional admin activation)

The removable USB manager now supports **RW** as well as **RO** mounting.
The new installer defaults to **RW**, but has not been executed on the Pi:
the remote project account cannot use passwordless sudo. The current flash
therefore remains mounted read-only under the existing UUID-specific fstab
entry until an administrator enables the manager.

One-time setup, using a Pi terminal with administrative access:

    cd ~/projects/RS-TV-HOME
    sudo bash scripts/install_family_usb_hotplug.sh rw

The installer backs up fstab, replaces the fixed-UUID mount rule with a
separate service, and selects the RW mode in /etc/default/rs-family-usb.
For a *currently mounted* USB, the manager tries a normal remount to RW
without disconnecting the photo frame. A write-protected/unclean filesystem
that refuses RW is **not** force-mounted. Different, supported USB sticks
can then mount at the same /mnt/family-usb path. The manager never mounts
the Pi boot card or chooses arbitrarily between multiple USB devices.

Switch back to read-only or writable mode at any time:

    sudo bash scripts/set_family_usb_mode.sh ro
    sudo bash scripts/set_family_usb_mode.sh rw

Check the actual mode, rather than trusting the configuration alone:

    findmnt -n -T /mnt/family-usb -o TARGET,FSTYPE,OPTIONS
    python3 scripts/family_usb_manager.py --check

**Safely eject before physically removing any writable USB drive**:

    sudo bash scripts/eject_family_usb.sh

This stops automatic remounting, flushes disk writes and performs a
non-lazy unmount. On success remove the drive. After inserting another:

    sudo systemctl start rs-family-usb-manager.service

Never simply pull out an RW flash drive during a transfer. Supported
filesystem types are FAT32, exFAT, NTFS and ext4. FAT/exFAT/NTFS mounts
assign files to the normal Pi user; ext4 keeps its Linux ownership and
permission bits, so some external ext4 drives may require manual permissions
before the Pi user can write. No existing files are modified automatically.
The photo frame's current view/delete/remove-from-view logic continues to
read the USB source and write album state or optimized media copies only
on the Pi; enabling RW does not by itself create a network upload/share.

To return to the original UUID-specific mounting configuration:

    sudo bash scripts/uninstall_family_usb_hotplug.sh

The uninstall script attempts to remount the current drive read-only and
retains the restored fstab in its original location. The archived pre-change
fstab backup remains under /etc/fstab.rs-family-usb-original.restored.

The root installation is deliberately optional; all mount selector tests
are executed with mocked system commands, never touching real flash media:

    python3 scripts/test_family_usb_manager.py
