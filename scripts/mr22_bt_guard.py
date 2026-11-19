#!/usr/bin/env python3
"""Conservative RPi3/BlueZ HCI fault guard for the paired Magic Remote.

Only considers recovery after a NEW burst of kernel hci0 frame errors
AND a stalled HID stream while both TV and HID status are connected.
An idle/asleep remote with no kernel errors is never recovered.
One auto-recovery at most per 30 minutes. No pairing changes.
"""
import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = Path.home() / '.cache' / 'rs-family-frame'
STAMP = STATE_DIR / 'mr22-bt-guard.json'
LOCK = STATE_DIR / 'mr22-bt-guard.lock'
REBOOT_ID = Path('/proc/sys/kernel/random/boot_id')
RECOVER = ROOT / 'scripts' / 'recover_magic_remote.py'
COOLDOWN = 30 * 60
ERROR_WINDOW = 110
ERROR_THRESHOLD = 6
HID_PROBE_SEC = 8


def recent_hci_error_count(kernel_text, uptime_seconds, window=ERROR_WINDOW):
    hits=0
    for line in kernel_text.splitlines():
        if 'Bluetooth: hci0:' not in line:
            continue
        if not ('Frame reassembly failed' in line or
                'Received unexpected HCI Event' in line):
            continue
        match=re.match(r'^\[\s*(\d+(?:\.\d+)?)\]',line)
        if not match:
            continue
        age=uptime_seconds-float(match.group(1))
        if 0<=age<=window:
            hits+=1
    return hits


def kernel_error_count():
    proc=subprocess.run(['dmesg'],capture_output=True,text=True,timeout=8)
    if proc.returncode:
        raise RuntimeError('Kernel Bluetooth log unreadable')
    uptime=float(Path('/proc/uptime').read_text().split()[0])
    return recent_hci_error_count(proc.stdout,uptime)


def fetch_status():
    cfg=json.loads((ROOT / '.local/config.json').read_text())
    host=cfg['BRIDGE_HOST']
    with urllib.request.urlopen('http://'+host+':8787/api/status',
                                timeout=4) as response:
        data=json.load(response)
    state=data['status']
    return {
        'hid':state.get('hid'),
        'tv':state.get('tv'),
        'frames':state.get('frames'),
        'pointer':data['settings'].get('pointer'),
    }


def healthy_or_idle(a,b,errors):
    """Return why recovery must NOT run; empty only for a confirmed fault."""
    if errors<ERROR_THRESHOLD:
        return 'no-new-hci-error-burst'
    for item in (a,b):
        if item['hid']!='connected' or item['tv']!='connected':
            return 'remote-or-tv-not-ready'
        if item['pointer'] is not True:
            return 'pointer-mode-disabled'
        if not isinstance(item['frames'],int):
            return 'hid-counter-unavailable'
    if b['frames']!=a['frames']:
        return 'hid-frames-are-progressing'
    return ''


def state_from_disk():
    try:
        if STAMP.is_symlink():
            raise OSError('Unsafe guard state link')
        if STAMP.exists() and STAMP.stat().st_mode & 0o077:
            raise OSError('Unsafe guard state mode')
        return json.loads(STAMP.read_text()) if STAMP.exists() else {}
    except (OSError,ValueError,TypeError):
        return {}


def run_guard(commit=False, delay=HID_PROBE_SEC):
    STATE_DIR.mkdir(mode=0o700,parents=True,exist_ok=True)
    STATE_DIR.chmod(0o700)
    lockfd=os.open(LOCK,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        try:
            fcntl.flock(lockfd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('MR22_GUARD: another check is already running',flush=True)
            return 0
        # First check kernel events. No network wait when radio has no errors.
        errors=kernel_error_count()
        if errors<ERROR_THRESHOLD:
            print('MR22_GUARD: no recent HCI fault burst, errors',errors,flush=True)
            return 0
        now=time.time()
        boot=REBOOT_ID.read_text().strip()
        state=state_from_disk()
        if state.get('boot')==boot and now-float(state.get('last_attempt',0))<COOLDOWN:
            print('MR22_GUARD: recovery cooldown, errors',errors,flush=True)
            return 0
        a=fetch_status()
        time.sleep(delay)
        b=fetch_status()
        # Re-evaluate error freshness, avoiding old bursts after probe delay.
        errors=kernel_error_count()
        reason=healthy_or_idle(a,b,errors)
        if reason:
            print('MR22_GUARD: no action:',reason,'errors',errors,flush=True)
            return 0
        print('MR22_GUARD: verified HCI burst + frozen HID',errors,'errors',
              'no frames during',delay,'s',flush=True)
        if not commit:
            print('MR22_GUARD: check-only; no Bluetooth reset',flush=True)
            return 0
        tmp=STAMP.with_suffix('.tmp')
        try:
            fd=os.open(tmp,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'w') as f:
                json.dump({'boot':boot,'last_attempt':now},f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp,STAMP)
        finally:
            tmp.unlink(missing_ok=True)
        try:
            result=subprocess.run([sys.executable,str(RECOVER),'--recover'],
                                  capture_output=True,text=True,timeout=115,
                                  cwd=str(ROOT))
            ok=result.returncode==0 and 'HID_STREAM_RECOVERED' in result.stdout
            print('MR22_GUARD: recovery attempted, HID recovered:',ok,flush=True)
        except subprocess.TimeoutExpired:
            print('MR22_GUARD: recovery timed out',flush=True)
            return 1
        return 0
    finally:
        os.close(lockfd)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',action='store_true',
                   help='Allow guarded recovery after confirmed radio fault')
    args=p.parse_args()
    try:
        return run_guard(commit=args.run)
    except (OSError,ValueError,RuntimeError,KeyError,TimeoutError) as exc:
        print('MR22_GUARD: check failed',type(exc).__name__,flush=True)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
