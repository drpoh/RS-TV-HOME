#!/usr/bin/env python3
"""Experimental local LG remote bridge, no kernel module."""
import argparse, json, math, os, select, statistics, time
from pathlib import Path
from probe import device, decode
BASE=Path(__file__).resolve().parent
TV='__RS_TV_HOST__'
KEYS={0x8040:'UP',0x8041:'DOWN',0x8006:'RIGHT',0x8007:'LEFT',0x807c:'HOME',0x8028:'BACK',0x8043:'MENU',0x8002:'VOLUMEUP',0x8003:'VOLUMEDOWN',0x8009:'MUTE',0x8001:'CHANNELDOWN',0x8072:'RED',0x8071:'GREEN',0x8063:'YELLOW',0x8061:'BLUE',**{0x8010+i:str(i) for i in range(10)}}
METHODS={'UP':'up','DOWN':'down','RIGHT':'right','LEFT':'left','HOME':'home','BACK':'back','MENU':'menu','MUTE':'mute','VOLUMEUP':'volume_up','VOLUMEDOWN':'volume_down','CHANNELDOWN':'channel_down',**{x:x.lower() for x in ('RED','GREEN','YELLOW','BLUE')},**{str(i):'num_'+str(i) for i in range(10)}}
def connect():
    from pywebostv.connection import WebOSClient
    from pywebostv.controls import InputControl
    state=BASE/'tv-registration.json'
    store=json.loads(state.read_text()) if state.exists() else {}
    c=WebOSClient(TV)
    c.connect()
    try:
        for status in c.register(store,timeout=45):
            if status==WebOSClient.PROMPTED: print('TV_CONFIRM_REQUIRED',flush=True)
            if status==WebOSClient.REGISTERED:
                temp=state.with_suffix('.tmp')
                fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
                with os.fdopen(fd,'w') as f: json.dump(store,f)
                os.chmod(temp,0o600); os.replace(temp,state)
                print('TV_REGISTERED',flush=True)
        inp=InputControl(c); inp.connect_input()
        print('POINTER_CONNECTED',flush=True)
        return c,inp
    except BaseException:
        c.close(); raise
def read_frame(fd,timeout=.2):
    if not select.select([fd],[],[],timeout)[0]: return None
    try: b=os.read(fd,1024)
    except BlockingIOError: return None
    if not b: raise OSError('HID closed')
    return decode(b) if len(b)==20 and b[0]==0xfd else None
def run(inp,seconds,xaxis,yaxis,gain):
    fd=os.open(device(),os.O_RDONLY|os.O_NONBLOCK)
    try:
        # Measured stationary values during the read-only 5-second probe.
        biases=[-1,5,0]
        print('LIVE_TEST_READY_MOVE_REMOTE',flush=True)
        end=time.monotonic()+seconds; lastkey=0; smooth=[0.,0.]; acc=[0.,0.]; sent=0; clicks=0; buttons=0; scrolls=0
        last=time.monotonic(); flush_at=last
        while time.monotonic()<end:
            d=read_frame(fd)
            now=time.monotonic()
            if d is None: continue
            dt=min(.025,max(.001,now-last));last=now
            _,axes,key,wheel=d
            g=[axes[i]-biases[i] for i in range(3)]
            for i,ax in enumerate((xaxis,yaxis)):
                v=g[abs(ax)-1]*(1 if ax>0 else -1)
                if abs(v)<100: v=0
                smooth[i]=.25*v+.75*smooth[i]
                if key==0: acc[i]=max(-120,min(120,acc[i]+smooth[i]*gain*dt))
            if key!=lastkey:
                if key==0x8044:
                    inp.click();clicks+=1
                elif key in (0x8040,0x8041,0x8006,0x8007,0x807c,0x8028):
                    getattr(inp,METHODS[KEYS[key]])();buttons+=1
                lastkey=key
                if key: acc=[0.,0.];smooth=[0.,0.]
            if wheel:
                # Scroll direction/scale provisional until on-screen test.
                inp.scroll(0,max(-120,min(120,-wheel*30)));scrolls+=1
            if now-flush_at>=.033:
                dx,dy=(max(-75,min(75,int(z))) for z in acc)
                if dx or dy: inp.move(dx,dy);sent+=1
                acc=[acc[0]-dx,acc[1]-dy];flush_at=now
        print('TEST_DONE',json.dumps(dict(moves=sent,clicks=clicks,buttons=buttons,scrolls=scrolls)),flush=True)
    finally: os.close(fd)
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--demo',action='store_true')
    p.add_argument('--test',type=int)
    p.add_argument('--xaxis',type=int,choices=[-3,-2,-1,1,2,3],default=3)
    p.add_argument('--yaxis',type=int,choices=[-3,-2,-1,1,2,3],default=-1)
    p.add_argument('--gain',type=float,default=.75)
    args=p.parse_args()
    os.umask(0o077)
    c=inp=None
    try:
        c,inp=connect()
        if args.demo:
            for dx,dy in [(25,0),(0,25),(-25,0),(0,-25)]:
                for _ in range(4): inp.move(dx,dy);time.sleep(.08)
                time.sleep(.3)
            print('POINTER_DEMO_SENT',flush=True)
        if args.test: run(inp,min(120,max(5,args.test)),args.xaxis,args.yaxis,args.gain)
    except Exception as e:
        # Do not log connection messages containing the private session URI.
        print('BRIDGE_ERROR',type(e).__name__,flush=True)
        return 1
    finally:
        if inp:
            try: inp.disconnect_input()
            except Exception: pass
        if c:
            try: c.close()
            except Exception: pass
    return 0
if __name__=='__main__': raise SystemExit(main())
