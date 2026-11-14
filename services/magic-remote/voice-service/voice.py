"""RS Magic Voice 0.1.0 — PTT-only, STT validation mode."""
import fcntl,json,os,queue,select,signal,stat,subprocess,sys,time
from pathlib import Path
from ws4py.client.threadedclient import WebSocketClient
from full_pipeline import notify_tv_diagnostic,speak_yandex
from split_pipeline import run
from state_reader import read_state
from metrics import append_result
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from probe import device,decode

ROOT=Path(__file__).resolve().parent
TOKEN=Path.home()/'.config/rs-magic-voice/token'
STATUS=ROOT/'status.json'
LAST=ROOT/'last-result.json'
HISTORY=ROOT/'timings.json'
URL='ws://__RS_HA_HOST__:8123/api/websocket'
PIPELINE='__RS_VOICE_PIPELINE__'
os.umask(0o077)

def status(phase,**fields):
    data=dict(version='0.6.2',mode='fast-hybrid-yandex-tv',phase=phase,updated=time.time(),**fields)
    tmp=STATUS.with_suffix('.tmp')
    tmp.write_text(json.dumps(data))
    tmp.replace(STATUS)
    if phase in ('recognized','completed','error','discarded'):
        tmp=LAST.with_suffix('.tmp')
        tmp.write_text(json.dumps(data))
        tmp.replace(LAST)

def token_read():
    fd=os.open(TOKEN,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'r') as f:
        s=os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077:
            raise PermissionError('Unsafe token permissions')
        token=f.read(8192).strip()
    if not token:raise ValueError('Missing token')
    return token

class Client(WebSocketClient):
    def __init__(self):
        self.messages=queue.Queue(maxsize=256)
        super().__init__(URL)
    def received_message(self,msg):
        if msg.is_text:
            self.messages.put_nowait(json.loads(str(msg)))
    def receive(self):
        return self.messages.get(timeout=130)
    def send_json(self,data):self.send(json.dumps(data))
    def send_pcm(self,data):self.send(data,binary=True)

def authenticate():
    c=Client()
    try:
        c.connect()
        if c.receive().get('type')!='auth_required':raise RuntimeError('Unexpected auth response')
        c.send_json({'type':'auth','access_token':token_read()})
        if c.receive().get('type')!='auth_ok':raise PermissionError('HA authentication rejected')
        return c
    except BaseException:
        try:c.close()
        except Exception:pass
        raise

def report(fd,op):
    b=bytearray([0xf9,op])
    n=fcntl.ioctl(fd,(3<<30)|(2<<16)|(ord('H')<<8)|6,b,True)
    if n!=2:raise OSError('Unexpected feature write length')

def msbc_frames(r):
    if len(r)!=124 or r[0]!=0xfe:return ()
    frames=[]
    for off in (4,64):
        b=r[off:off+60]
        if b[0]==1 and b[1] in (8,56,200,248) and b[2]==0xad:
            frames.append(b[2:59])
    return tuple(frames)

def capture(fd):
    armed=False
    while True:
        if not select.select([fd],[],[],.5)[0]:continue
        r=os.read(fd,256)
        if not r:raise OSError('HID disconnected')
        d=decode(r)
        if d is None:continue
        k=d[2]
        if k==0:armed=True
        if armed and k==0x808b:break
    frames=[];started=time.monotonic();attempted=False;released=False
    status('recording')
    try:
        attempted=True
        report(fd,3)
        while time.monotonic()-started<8 and len(frames)<1100:
            if not select.select([fd],[],[],.1)[0]:continue
            r=os.read(fd,256)
            if not r:raise OSError('HID disconnected')
            d=decode(r)
            if d is not None and d[2]==0:
                released=True;break
            frames.extend(msbc_frames(r))
    finally:
        if attempted:report(fd,4)
    # Do not process incomplete/interrupted or timeout captures.
    if not released:return None
    if len(frames)<40:return None
    p=subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-f','sbc','-i','pipe:0','-f','s16le','-ac','1','-ar','16000','pipe:1'],input=b''.join(frames),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10)
    if p.returncode or not p.stdout or len(p.stdout)%2:raise RuntimeError('Decode failed')
    return p.stdout

def stop(*_):raise KeyboardInterrupt
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)

def main():
    # Prove authentication before enabling PTT capture.
    c=authenticate();c.close()
    while True:
        fd=None;c=None
        try:
            fd=os.open(device(),os.O_RDWR|os.O_NONBLOCK)
            status('ready')
            pcm=capture(fd)
            os.close(fd);fd=None
            if pcm is None:
                status('discarded');continue
            status('recognizing',seconds=round(len(pcm)/32000,3))
            c=authenticate()
            t=time.monotonic()
            get_state=lambda entity:read_state(entity,token_read())
            result=run(c.send_json,c.receive,c.send_pcm,pcm,PIPELINE,get_state,progress=status)
            reply=result.pop('reply')
            status('completed',**result,notification_ok=False,speaker_ok=False,elapsed=round(time.monotonic()-t,2))
            spoken=False;notified=False;speaker_seconds=None;notification_seconds=None;notification_reason='empty_reply'
            if reply:
                status('speaking')
                begin=time.monotonic()
                try:spoken=speak_yandex(c.send_json,c.receive,reply)
                except Exception:pass
                speaker_seconds=round(time.monotonic()-begin,2)
                begin=time.monotonic()
                try:notified,notification_reason=notify_tv_diagnostic(c.send_json,c.receive,reply,get_state)
                except Exception:notification_reason='transport_error'
                notification_seconds=round(time.monotonic()-begin,2)
            status('completed',**result,notification_ok=notified,speaker_ok=spoken,speaker_seconds=speaker_seconds,notification_seconds=notification_seconds,notification_reason=notification_reason,elapsed=round(time.monotonic()-t,2))
            try:append_result(HISTORY,json.loads(LAST.read_text()))
            except (OSError,ValueError):pass
            print('Assist run completed',flush=True)
            time.sleep(1)
        except (OSError,RuntimeError,ValueError,queue.Empty,subprocess.TimeoutExpired) as e:
            status('error',error=type(e).__name__)
            time.sleep(2)
        finally:
            if fd is not None:os.close(fd)
            if c is not None:
                try:c.close()
                except Exception:pass

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:status('stopped')
