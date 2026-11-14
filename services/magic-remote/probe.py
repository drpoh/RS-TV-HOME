#!/usr/bin/env python3
"""Read-only diagnostic for the paired LG Magic Remote."""
import argparse, collections, os, select, struct, time
from pathlib import Path

MAC = "__RS_REMOTE_MAC__"
def device():
    for d in Path('/sys/bus/hid/devices').glob('0005:000F:3412.*'):
        try:
            props = dict(line.split('=',1) for line in (d/'uevent').read_text().splitlines() if '=' in line)
            if props.get('HID_UNIQ','').lower() != MAC:
                continue
            for h in (d/'hidraw').glob('hidraw*'):
                p=Path('/dev')/h.name
                if p.exists(): return p
        except OSError:
            continue
    raise RuntimeError("Paired remote HID node not present. Press OK.")

def decode(b):
    if len(b) < 20 or b[0] != 0xfd: return None
    return (int.from_bytes(b[1:3],'little'), struct.unpack('>6h', b[5:17]), int.from_bytes(b[17:19],'big'), struct.unpack('b',b[19:20])[0])

def run(seconds):
    p=device()
    print('DEVICE',p,flush=True)
    fd=os.open(p,os.O_RDONLY|os.O_NONBLOCK)
    counts=collections.Counter(); buttons=collections.Counter(); wheel=0
    lo=[None]*6;hi=[None]*6;last=None;examples=[];motion=0
    t=time.monotonic()
    try:
        while time.monotonic()-t < seconds:
            if not select.select([fd],[],[],0.25)[0]: continue
            b=os.read(fd,1024)
            if not b: break
            counts[(hex(b[0]),len(b))]+=1
            d=decode(b)
            if d is None: continue
            counter,axes,button,w=d
            motion+=1
            for i,x in enumerate(axes):
                lo[i]=x if lo[i] is None else min(lo[i],x)
                hi[i]=x if hi[i] is None else max(hi[i],x)
            if button!=last:
                buttons[hex(button)]+=1
                print('BUTTON_CANDIDATE',hex(button),flush=True)
                last=button
            if w: wheel+=w
            if len(examples)<3: examples.append(b[:20].hex())
    finally: os.close(fd)
    print('REPORT_COUNTS',dict(counts))
    print('FD_FRAMES',motion,'AXIS_MIN',lo,'AXIS_MAX',hi,'WHEEL_SUM_CANDIDATE',wheel)
    print('BUTTON_TRANSITIONS',dict(buttons))
    print('FD_HEADER_SAMPLES',examples)
    print('NOTE: FD fields are candidate MR20 offsets, not validated for MR22 yet.')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--seconds',type=int,default=20);a.add_argument('--self-test',action='store_true');args=a.parse_args()
    if args.self_test:
        b=bytes.fromhex('fd010000fd')+struct.pack('>6h',-1,2,-3,4,-5,6)+bytes.fromhex('8044ff')
        assert decode(b)==(1,(-1,2,-3,4,-5,6),0x8044,-1)
        assert decode(bytes.fromhex('fe010203')) is None
        print('SELF_TEST_OK')
    else:
        try: run(max(1,min(args.seconds,60)))
        except (PermissionError,RuntimeError,OSError) as e: print('PROBE_ERROR:',e);raise SystemExit(1)
