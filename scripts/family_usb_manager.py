#!/usr/bin/env python3
"""Read/write-capable hot-swap mount manager for removable USB media.

Designed for an explicitly-installed, root-owned systemd service. Scans only
USB block devices, leaves unrelated mounted devices alone and never writes to
the mounted filesystem. Does NOT run automatically from the project checkout.
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

TARGET = Path('/mnt/family-usb')
SUPPORTED = frozenset(('vfat', 'exfat', 'ntfs', 'ntfs3', 'ext4'))
INTERVAL = 10
STOP = False


def run(command, timeout=12):
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout)


def discover():
    """Return available removable USB partitions (never the Pi boot card)."""
    result = run(['/usr/bin/lsblk', '-J',
                  '-o', 'NAME,PATH,TRAN,TYPE,FSTYPE,MOUNTPOINTS,UUID,RM'])
    if result.returncode:
        raise OSError('USB device discovery failed')
    data = json.loads(result.stdout)
    found = []
    for disk in data.get('blockdevices', []):
        if disk.get('tran') != 'usb' or disk.get('type') != 'disk':
            continue
        # USB disks may be partitioned or formatted as superfloppy devices.
        for child in disk.get('children') or [disk]:
            fs = (child.get('fstype') or '').lower()
            path = child.get('path') or ''
            if child.get('type') not in ('part', 'disk') or fs not in SUPPORTED:
                continue
            if not path.startswith('/dev/') or not path[5:].replace('_', '').isalnum():
                continue
            mounts = [x for x in (child.get('mountpoints') or []) if x]
            found.append({'path': path, 'fstype': fs,
                          'uuid': child.get('uuid') or '',
                          'mounted_elsewhere': any(m != str(TARGET) for m in mounts)})
    return found


def current_mount():
    result = run(['/usr/bin/findmnt', '-rn', '-M', str(TARGET),
                  '-o', 'SOURCE,FSTYPE,OPTIONS'])
    if result.returncode or not result.stdout.strip():
        return None
    pieces = result.stdout.strip().split(None, 2)
    if len(pieces) < 3:
        return None
    return {'path': pieces[0], 'fstype': pieces[1],
            'readonly': 'ro' in pieces[2].split(',')}


def mount_options(fstype, mode='ro'):
    """Always prevent executable/setuid/device files; only mode affects writes."""
    if mode not in ('rw','ro'):
        raise ValueError('Invalid USB mount mode')
    common=mode+',nosuid,nodev,noexec'
    if fstype == 'vfat':
        return common+',uid=1000,gid=1000,umask=0022,utf8'
    if fstype in ('exfat','ntfs','ntfs3'):
        return common+',uid=1000,gid=1000,umask=0022'
    return common


def reconcile(devices, mounted, readonly_check=lambda: True, call=run,
              observed_uuid=None, mode='ro'):
    """Pure-ish decision engine; bounded calls and conservative decisions.

    Returns status rather than trying to pick a drive if more than one eligible
    USB is present. A current mount is retained while its partition exists.
    """
    if mode not in ('ro', 'rw'):
        raise ValueError('Invalid USB mount mode')
    candidates=[d for d in devices if not d['mounted_elsewhere']]
    if mounted:
        for d in devices:
            same_device = (
                d['path'] == mounted['path'] and readonly_check()
                and (not observed_uuid or not d['uuid']
                     or observed_uuid == d['uuid'])
            )
            if same_device:
                if mounted['readonly'] == (mode == 'ro'):
                    return 'existing-mount-preserved'
                # Changing an existing flash from RO to RW is allowed only
                # after the administrator enabled RW in the root service.
                # Do not bypass filesystem write protection or a dirty volume.
                options = 'remount,'+mount_options(d['fstype'], mode)
                result=call(['/usr/bin/mount','-o',options,str(TARGET)],timeout=20)
                if result.returncode:
                    return 'remount-failed'
                return 'remounted-readwrite' if mode == 'rw' else 'remounted-readonly'
        # Stale, removed or writable mount: do not force-unmount an unknown device.
        if not mounted['path'].startswith('/dev/sd'):
            return 'foreign-mount-left-alone'
        if any(d['path']==mounted['path'] for d in devices):
            # A rapidly exchanged flash drive may reuse /dev/sda1 before
            # the next poll. A DIFFERENT UUID identifies the new drive.
            replaced=(observed_uuid and any(
                d['path']==mounted['path'] and d['uuid'] and
                d['uuid']!=observed_uuid for d in devices))
            if not replaced:
                return 'mounted-device-needs-manual-check'
        result = call(['/usr/bin/umount', '-l', str(TARGET)])
        if result.returncode:
            return 'stale-mount-cannot-detach'
    if len(candidates) != 1:
        return 'no-usb' if not candidates else 'multiple-usb-select-manually'
    selected=candidates[0]
    result=call(['/usr/bin/mount', '-t', selected['fstype'],
                 '-o', mount_options(selected['fstype'], mode),
                 selected['path'], str(TARGET)], timeout=20)
    return ('mounted-readwrite' if mode == 'rw' else 'mounted-readonly') if not result.returncode else 'mount-failed'


def ready():
    if TARGET.is_symlink() or not TARGET.is_dir():
        raise OSError('Untrusted media mount directory')
    if os.geteuid() != 0:
        raise PermissionError('USB manager requires the administrator installer')


def stop(signum, frame):
    global STOP
    STOP=True


def mount_readable():
    try:
        with os.scandir(TARGET) as it:
            next(it, None)
        return True
    except OSError:
        return False


def configured_mode():
    value=os.environ.get('RS_FAMILY_USB_MODE')
    if value is None:
        try:
            content=Path('/etc/default/rs-family-usb').read_text().strip()
            if content.startswith('RS_FAMILY_USB_MODE='):
                value=content.split('=',1)[1]
        except OSError:
            pass
    mode=(value or 'ro').strip().lower()
    if mode not in ('ro','rw'):
        raise ValueError('Invalid RS_FAMILY_USB_MODE')
    return mode


def main():
    mode=configured_mode()
    if mode not in ('ro','rw'):
        raise SystemExit('Invalid RS_FAMILY_USB_MODE')
    if '--check' in sys.argv[1:]:
        devices=discover()
        mounted=current_mount()
        print('USB_SOURCE_CHECK', 'usb_disks', len(devices),
              'mount_mode_configured',mode,
              'current_mode', ('ro' if mounted and mounted['readonly'] else 'rw' if mounted else 'none'),
              'current_is_supported',
              bool(mounted and any(d['path']==mounted['path'] for d in devices)))
        return
    ready()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    last=None
    previous_uuid=None
    while not STOP:
        try:
            devices=discover()
            mounted=current_mount()
            status=reconcile(devices,mounted,readonly_check=mount_readable,
                             observed_uuid=previous_uuid,mode=mode)
            if status in ('existing-mount-preserved','mounted-readonly',
                          'mounted-readwrite','remounted-readwrite','remounted-readonly'):
                current=current_mount()
                if current:
                    previous_uuid=next((d['uuid'] for d in devices
                                       if d['path']==current['path']),previous_uuid)
            elif status=='no-usb':
                previous_uuid=None
        except (OSError, ValueError, subprocess.SubprocessError):
            status='usb-check-error'
        if status!=last:
            print('RS family USB:',status,flush=True)
            last=status
        time.sleep(INTERVAL)


if __name__=='__main__':
    main()
