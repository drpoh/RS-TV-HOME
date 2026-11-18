"""Prepare streaming-friendly copies on the Raspberry Pi; original media is never changed."""
import server
from collections import Counter
import time

if __name__=='__main__':
    counts=Counter()
    start=time.monotonic()
    for p,kind in server.entries().values():
        if kind!='video/mp4':continue
        try:
            cached=server.prepare_video(p)
            if server.video_cache_ready(cached):counts['ready']+=1
        except Exception:
            counts['failed']+=1
        counts['total']+=1
        if counts['total']%20==0:
            print('VIDEO_PREP_PROGRESS',counts['total'],'ready',counts['ready'],'failed',counts['failed'],flush=True)
    print('VIDEO_PREP_COMPLETE',dict(counts),'seconds',round(time.monotonic()-start,1),flush=True)
