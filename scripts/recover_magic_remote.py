#!/usr/bin/env python3
"""Safely diagnose/recover the paired LG MR22 Bluetooth HID on Raspberry Pi.

Run --check for non-invasive diagnosis. --recover power-cycles only the Pi's
Bluetooth radio, retaining existing pairing, only if no other BT devices are
connected. Restores the user remote service on every exit, and never touches
TV settings, app packages or family media.
"""
import argparse
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = 'rs-magic-remote.service'
REMOTE_NAME = 'LGE MR22'
MAC = re.compile(r'(?i)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b')


def run(cmd, timeout=15):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def devices(kind='Paired'):
    response=run(['bluetoothctl','devices',kind],timeout=7)
    if response.returncode:
        raise OSError('Unable to list Bluetooth devices')
    found=[]
    for line in response.stdout.splitlines():
        match=MAC.search(line)
        if match and line.strip().startswith('Device '):
            found.append((match.group(0),line[match.end():].strip()))
    return found


def remote_info(address):
    r=run(['bluetoothctl','info',address],timeout=6)
    if r.returncode:
        return {'paired':False,'trusted':False,'connected':False}
    return {
        'paired':'Paired: yes' in r.stdout,
        'trusted':'Trusted: yes' in r.stdout,
        'connected':'Connected: yes' in r.stdout,
    }


def controller_is_powered():
    r=run(['bluetoothctl','show'],timeout=7)
    return r.returncode==0 and 'Powered: yes' in r.stdout


def acquire_status():
    c=json.loads((ROOT/'.local/config.json').read_text())
    host=c['BRIDGE_HOST']
    with urllib.request.urlopen(f'http://{host}:8787/api/status',timeout=4) as res:
        return json.load(res)['status']


def bluetooth_power(enabled):
    state='on' if enabled else 'off'
    r=run(['bluetoothctl','--timeout','10','power',state],timeout=13)
    return r.returncode==0 and (
        f'Changing power {state} succeeded' in r.stdout
        or (controller_is_powered()==enabled)
    )


def status_snapshot():
    try:
        x=acquire_status()
        return {k:x.get(k) for k in ('hid','tv','frames','moves','mode','error')}
    except (OSError,ValueError,KeyError):
        return {'error':'status unavailable'}


def recover(allow_recovery):
    paired=devices('Paired')
    matches=[mac for mac,name in paired if name==REMOTE_NAME]
    if len(matches)!=1:
        raise RuntimeError('MR22 is not uniquely paired; do not reset the radio')
    mac=matches[0]
    connected=devices('Connected')
    others=[name for address,name in connected if address.lower()!=mac.lower()]
    if others:
        raise RuntimeError('Other Bluetooth devices are connected; refusing radio reset')
    start_state=remote_info(mac)
    print('PAIRED',start_state['paired'],'TRUSTED',start_state['trusted'],
          'CONNECTED',start_state['connected'],flush=True)
    print('REMOTE_STATUS',status_snapshot(),flush=True)
    if not start_state['paired'] or not start_state['trusted']:
        raise RuntimeError('MR22 bonding not ready; no changes made')
    if not allow_recovery:
        print('CHECK_ONLY: radio and controller left unchanged',flush=True)
        return
    env=os.environ.copy()
    uid=os.getuid()
    env.setdefault('XDG_RUNTIME_DIR',f'/run/user/{uid}')
    env.setdefault('DBUS_SESSION_BUS_ADDRESS',f'unix:path=/run/user/{uid}/bus')
    service=lambda action: subprocess.run(
        ['systemctl','--user',action,SERVICE],capture_output=True,
        text=True,timeout=15,env=env)
    was_powered=controller_is_powered()
    if not was_powered:
        raise RuntimeError('Bluetooth radio is already off; do not change its state')
    try:
        stopped=service('stop')
        if stopped.returncode:
            raise RuntimeError('Could not stop the remote service')
        if not bluetooth_power(False):
            raise RuntimeError('Could not power down Bluetooth')
        time.sleep(2)
        if not bluetooth_power(True):
            raise RuntimeError('Could not power Bluetooth back on')
        time.sleep(3)
        if not remote_info(mac)['connected']:
            # Try reconnecting just the already-paired MR22; never remove pairing.
            r=run(['bluetoothctl','--timeout','14','connect',mac],timeout=17)
            if r.returncode:
                print('CONNECT_RETRY_NEEDED',flush=True)
        print('BT_CONNECTED_AFTER_RECOVERY',remote_info(mac)['connected'],flush=True)
    finally:
        if not controller_is_powered():
            bluetooth_power(True)
        restarted=service('start')
        print('REMOTE_SERVICE_RESTORED',restarted.returncode==0,flush=True)
    first=status_snapshot().get('frames',0) or 0
    for _ in range(6):
        time.sleep(2)
        later=status_snapshot()
        frames=later.get('frames')
        if later.get('hid')=='connected' and later.get('tv')=='connected' and isinstance(frames,int) and frames>first:
            print('HID_STREAM_RECOVERED',frames-first,'new frames',flush=True)
            return
    print('HID_STREAM_NOT_CONFIRMED: wake MR22 with OK and move it',flush=True)


def main():
    p=argparse.ArgumentParser(description='LG MR22 Bluetooth recovery (paired only)')
    choice=p.add_mutually_exclusive_group(required=True)
    choice.add_argument('--check',action='store_true')
    choice.add_argument('--recover',action='store_true')
    args=p.parse_args()
    recover(args.recover)


if __name__=='__main__':
    main()
