import json, os, time, threading, secrets, socket, select, math, subprocess, collections
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from bridge import connect,read_frame,device,METHODS
from precision_v3 import Precision
from recovery import SilenceRecovery,WorkerDeadline
from profiles import PROFILE,RANGES,SPECIAL,APPS,SHORTCUT_DEFAULTS,allowed,motion_of
BASE=Path(__file__).resolve().parent
PATH=BASE/'settings-v2.json'
HOST='__RS_BRIDGE_HOST__'; PORT=8787
DEFAULT={'gain':8.0,'xaxis':3,'yaxis':1,'deadzone':90,'pointer':True,'keys':{'UP':0x8040,'DOWN':0x8041,'LEFT':0x8007,'RIGHT':0x8006,'OK':0x8044,'HOME':0x807c,'BACK':0x8028}}
SET=json.loads(PATH.read_text()) if PATH.exists() else DEFAULT.copy()
SET.setdefault('smoothing',60)
SET.setdefault('acceleration',True)
SET.setdefault('auto_bias',True)
if 'sweep' not in SET:
    SET['sweep']=180
    SET['gain']=12.0
SET.setdefault('shortcuts',SHORTCUT_DEFAULTS.copy())
SAVED=motion_of(SET)
LOCK=threading.RLock()
STATE={'tv':'offline','hid':'waiting','frames':0,'moves':0,'buttons':0,'last_code':'—','last_action':'—','key_counts':{},'shortcut_result':'','bias':[-1,5,0],'mode':'cursor','motion_profile':'precision-v3','learn':None,'learn_until':0,'error':''}
TOKEN=secrets.token_urlsafe(24)
TV_KEY=(BASE/'tv-menu-key').read_text().strip()
TV_IP='__RS_TV_HOST__'
DEADLINE=WorkerDeadline()
EXTRA={'VOLUMEUP':'volume_up','VOLUMEDOWN':'volume_down','MUTE':'mute','CHANNELUP':'channel_up','CHANNELDOWN':'channel_down','MENU':'menu','INFO':'info','EXIT':'exit','RED':'red','GREEN':'green','YELLOW':'yellow','BLUE':'blue','PLAY':'play','PAUSE':'pause','STOP':'stop',**{str(i):'num_'+str(i) for i in range(10)}}
ACTIONS=list(DEFAULT['keys'])+list(EXTRA)+['MODE','NETFLIX','MOVIES','PRIME']
REPEATABLE=('UP','DOWN','LEFT','RIGHT','VOLUMEUP','VOLUMEDOWN','CHANNELUP','CHANNELDOWN')
class BiasTracker:
    def __init__(self):
        self.base=[-1.,5.,0.]
        self.bias=self.base[:];self.window=collections.deque(maxlen=150)
    def update(self,axes,quiet):
        if not quiet or any(abs(axes[i]-self.base[i])>60 for i in range(3)):
            self.window.clear();return
        self.window.append(tuple(axes))
        if len(self.window)<150:return
        for i in range(6):
            a=[x[i] for x in self.window]
            if max(a)-min(a)>(18 if i<3 else 45):return
        for i in range(3):
            avg=sum(x[i] for x in self.window)/len(self.window)
            self.bias[i]=max(self.base[i]-60,min(self.base[i]+60,.998*self.bias[i]+.002*avg))
def save(commit=False):
    if commit:
        SAVED.update(motion_of(SET))
    data=SET.copy();data.update(SAVED)
    p=PATH.with_suffix('.tmp');p.write_text(json.dumps(data));os.chmod(p,0o600);os.replace(p,PATH)
def shortcut(c,slot,target):
    if target=='none':setstate(shortcut_result=slot+': не назначено');return
    from pywebostv.controls import ApplicationControl,Application
    label,appid=APPS[target]
    setstate(shortcut_result='Открываем '+label)
    def result(ok,res):
        setstate(shortcut_result=label+(': команда принята' if ok else ': запуск не подтверждён'))
    ApplicationControl(c).launch(Application({'id':appid,'title':label}),callback=result,timeout=8)
def snapshot():
    with LOCK:
        if STATE['learn'] and time.monotonic()>STATE['learn_until']:STATE['learn']=None
        return {'settings':SET.copy(),'defaults':PROFILE.copy(),'saved':SAVED.copy(),'dirty':motion_of(SET)!=SAVED,'apps':{k:v[0] for k,v in APPS.items()},'status':{k:v for k,v in STATE.items() if k!='learn_until'}}
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,body,typ='application/json',code=200):
        if isinstance(body,dict): body=json.dumps(body).encode()
        self.send_response(code);
        if self.client_address[0]==TV_IP:self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Content-Type',typ);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path=='/':self.reply((BASE/'menu.html').read_text().replace('__TOKEN__',TOKEN).encode(),'text/html; charset=utf-8')
        elif self.path=='/api/status':self.reply(snapshot())
        else:self.reply({},code=404)
    def do_POST(self):
        try:
            n=int(self.headers.get('Content-Length',0))
            if not 0<n<=4096: raise ValueError()
            d=json.loads(self.rfile.read(n))
            if not isinstance(d,dict):raise ValueError()
            tvkey=d.pop('_tv_key',None)
            if self.headers.get('X-RS-Token')!=TOKEN and not (self.client_address[0]==TV_IP and tvkey==TV_KEY):
                self.reply({},code=403);return
            with LOCK:
                if self.path=='/api/settings':
                    candidate=SET.copy()
                    for k,v in d.items():
                        if k=='gain' and type(v) in (float,int) and RANGES[k][0]<=v<=RANGES[k][1]: candidate[k]=float(v)
                        elif k in ('xaxis','yaxis') and type(v)==int and v in (-3,-2,-1,1,2,3): candidate[k]=v
                        elif k=='deadzone' and type(v)==int and RANGES[k][0]<=v<=RANGES[k][1]:candidate[k]=v
                        elif k in ('pointer','acceleration','auto_bias') and type(v)==bool: candidate[k]=v
                        elif k=='sweep' and type(v)==int and RANGES[k][0]<=v<=RANGES[k][1]:candidate[k]=v
                        elif k=='smoothing' and type(v)==int and RANGES[k][0]<=v<=RANGES[k][1]:candidate[k]=v
                        else: raise ValueError()
                    if abs(candidate['xaxis'])==abs(candidate['yaxis']):raise ValueError()
                    SET.update(candidate)
                elif self.path=='/api/profile':
                    op=d.get('operation')
                    if op=='save':save(commit=True)
                    elif op=='default':SET.update(PROFILE)
                    elif op=='restore':SET.update(SAVED)
                    else:raise ValueError()
                elif self.path=='/api/shortcut':
                    slot,target=d.get('slot'),d.get('target')
                    if not isinstance(slot,str) or not isinstance(target,str) or not allowed(slot,target):raise ValueError()
                    SET['shortcuts'][slot]=target;save()
                elif self.path=='/api/learn':
                    a=d.get('action')
                    if a not in ACTIONS and a is not None:raise ValueError()
                    STATE['learn']=a;STATE['learn_until']=time.monotonic()+20
                else:self.reply({},code=404);return
            self.reply(snapshot())
        except (ValueError,TypeError,OSError):self.reply({'error':'invalid request'},code=400)
def setstate(**kw):
    with LOCK:STATE.update(kw)
def close(c,inp):
    if inp:
        try:inp.disconnect_input()
        except Exception:pass
    if c:
        try:c.close()
        except Exception:pass
def radio_recover():
    address='__RS_REMOTE_ADDRESS_VARIANT_A__'
    info=subprocess.run(['bluetoothctl','info',address],capture_output=True,text=True,timeout=4)
    if 'Paired: yes' not in info.stdout or 'Trusted: yes' not in info.stdout:
        return False
    if 'Connected: yes' in info.stdout:
        subprocess.run(['bluetoothctl','--timeout','6','disconnect',address],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=8)
        time.sleep(.5)
    result=subprocess.run(['bluetoothctl','--timeout','8','connect',address],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
    return result.returncode==0

def worker_watchdog():
    while True:
        time.sleep(1)
        if DEADLINE.expired():
            print('WORKER_WATCHDOG',DEADLINE.stage,flush=True)
            os._exit(1)

def worker():
    fd=None;c=inp=None;retry=0;bt_retry=0;tv_check=0;lastkey=0;hold=0;nextrepeat=0;lastmove=0;nav_until=0;last=flush=time.monotonic();acc=[0.,0.];sm=[0.,0.];tracker=BiasTracker();motion=Precision();resume=0;profile=None
    recovery=SilenceRecovery(time.monotonic())
    while True:
        DEADLINE.arm('loop',10)
        try:
            if fd is None:
                fd=os.open(device(),os.O_RDONLY|os.O_NONBLOCK)
                motion.reset()
                setstate(hid='connected',error='');lastkey=0;acc=[0.,0.];sm=[0.,0.];last=time.monotonic()
            now=time.monotonic()
            if inp is not None and now>=tv_check:
                tv_check=now+15
                try:
                    if c.terminated or inp.mouse_ws.terminated:raise OSError('TV socket closed')
                    with socket.create_connection(('__RS_TV_HOST__',3000),timeout=1):pass
                except Exception:
                    close(c,inp);c=inp=None;setstate(tv='offline');retry=now+3
                    acc=[0.,0.];sm=[0.,0.]
            if inp is None and now>=retry:
                DEADLINE.arm("tv_connect",75)
                retry=now+8
                try:
                    with socket.create_connection(('__RS_TV_HOST__',3000),timeout=1):pass
                    c,inp=connect();setstate(tv='connected');tv_check=time.monotonic()+15;last=time.monotonic();acc=[0.,0.];sm=[0.,0.]
                except Exception:close(c,inp);c=inp=None;setstate(tv='offline')
            DEADLINE.arm("hid_read",10)
            d=read_frame(fd,.15);now=time.monotonic()
            if d is None:
                action=recovery.action(now)
                if action:
                    os.close(fd);fd=None;lastkey=0;motion.reset()
                    setstate(hid='recovering',error='')
                    if action=='reopen':
                        print('HID_REOPEN_AFTER_SILENCE',flush=True)
                    else:
                        DEADLINE.arm('bluetooth_reconnect',35)
                        print('HID_RADIO_RECOVERY',flush=True)
                        try:radio_recover()
                        except (OSError,subprocess.TimeoutExpired):pass
                    # A new valid HID report re-arms the silence policy.
                continue
            recovery.report(now)
            elapsed=now-last;last=now
            if elapsed>.10:
                motion.reset();acc=[0.,0.];flush=now
            dt=min(.025,max(.002,elapsed))
            _,axes,key,wheel=d
            if key and (key & 0xff00)!=0x8000:
                motion.reset();acc=[0.,0.];continue
            with LOCK:
                STATE['frames']+=1
                if STATE['learn'] and now>STATE['learn_until']:STATE['learn']=None
                learning=STATE['learn'];cfg=SET.copy();keys=SET['keys'].copy()
                if key and key!=lastkey and (key & 0xff00)==0x8000:
                    STATE['last_code']=hex(key)
                    if learning:
                        other=next((a for a,v in SET['keys'].items() if a!=learning and v==key),None)
                        if other:
                            STATE['last_action']='occupied '+other
                        else:
                            SET['keys'][learning]=key;save()
                            STATE['last_action']='learned '+learning
                        STATE['learn']=None
            newprofile=tuple(cfg[k] for k in ('gain','sweep','deadzone','smoothing','acceleration','xaxis','yaxis','pointer','auto_bias'))
            if profile!=newprofile:
                profile=newprofile;motion.reset();acc=[0.,0.]
            tracker.update(axes,not key and not wheel and not learning and cfg['auto_bias'])
            if STATE['frames']%100==0:
                setstate(bias=[round(v,1) for v in tracker.bias])
            if learning:
                hold=now+1.2;motion.reset();acc=[0.,0.];lastkey=key;continue
            action=next((a for a,k in keys.items() if k==key),None)
            edge=key and key!=lastkey
            repeat=key and key==lastkey and action in REPEATABLE and now>=nextrepeat
            if key:
                hold=now+(1.5 if action in ('UP','DOWN','LEFT','RIGHT') else .25);acc=[0.,0.];sm=[0.,0.]
            if edge:nextrepeat=now+.45
            elif repeat:nextrepeat=now+.15
            if edge and action=='MODE':
                with LOCK:
                    SET['pointer']=not SET['pointer'];save()
                    STATE['last_action']='MODE';STATE['key_counts']['MODE']=STATE['key_counts'].get('MODE',0)+1
                cfg['pointer']=SET['pointer'];acc=[0.,0.];sm=[0.,0.]
            if inp:
                DEADLINE.arm('tv_send',10)
                try:
                    if (edge or repeat) and action and action!='MODE':
                        if action in SPECIAL and cfg['shortcuts'].get(action,'none')!='native':
                            if edge:shortcut(c,action,cfg['shortcuts'].get(action,'none'))
                        elif action=='OK':
                            if cfg['pointer'] and now-lastmove<3 and now>=nav_until:inp.click()
                            else:inp.ok()
                        else:
                            getattr(inp,EXTRA.get(action,action.lower()))()
                            if action in ('UP','DOWN','LEFT','RIGHT'):nav_until=now+2.5
                        with LOCK:STATE['buttons']+=1;STATE['last_action']=action;STATE['key_counts'][action]=STATE['key_counts'].get(action,0)+1
                    if wheel:inp.scroll(0,max(-120,min(120,-wheel*30)));hold=now+1.0
                    if action in ('UP','DOWN','LEFT','RIGHT') and key:resume=now+2.5
                    moving=max(abs(axes[i]-tracker.bias[i]) for i in range(3))>max(300,cfg['deadzone']*3)
                    if now>=hold and now<resume and moving:resume=now
                    setstate(mode='cursor' if cfg['pointer'] and now>=resume else 'buttons')
                    if now>=max(hold,resume) and cfg['pointer'] and not key:
                        bias=tracker.bias if cfg['auto_bias'] else tracker.base
                        x,y=((axes[abs(ax)-1]-bias[abs(ax)-1])*(1 if ax>0 else -1)
                             for ax in (cfg['xaxis'],cfg['yaxis']))
                        dx,dy=motion.sample(x,y,dt,cfg['gain'],cfg['deadzone'],cfg['smoothing'],cfg['acceleration'],cfg['sweep'])
                        dx,dy=motion.emit(dx,dy)
                        acc=[0.,0.];flush=now
                        if dx or dy:
                            inp.move(dx,dy);lastmove=now
                            with LOCK:STATE['moves']+=1
                    else:
                        motion.reset();acc=[0.,0.];flush=now
                except Exception:
                    close(c,inp);c=inp=None;setstate(tv='offline');retry=now+3
            lastkey=key
        except (OSError,RuntimeError) as e:
            DEADLINE.arm("hid_recovery",35)
            if fd is not None:os.close(fd);fd=None
            denied=isinstance(e,PermissionError)
            setstate(hid='waiting',error='HID permission denied' if denied else 'HID not available')
            now=time.monotonic()
            if not denied and now>=bt_retry:
                bt_retry=now+25
                try:
                    info=subprocess.run(['bluetoothctl','info','__RS_REMOTE_ADDRESS_VARIANT_A__'],capture_output=True,text=True,timeout=4)
                    if 'Paired: yes' in info.stdout and 'Trusted: yes' in info.stdout and 'Connected: no' in info.stdout:
                        subprocess.run(['bluetoothctl','--timeout','8','connect','__RS_REMOTE_ADDRESS_VARIANT_A__'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
                except (OSError,subprocess.TimeoutExpired):pass
            if inp is not None and (c.terminated or inp.mouse_ws.terminated):
                close(c,inp);c=inp=None;setstate(tv='offline')
            time.sleep(2)
def supervised_worker():
    try:worker()
    except Exception as e:
        print('WORKER_FAILED',type(e).__name__,flush=True)
        os._exit(1)
def main():
    os.umask(0o077)
    with LOCK:save(commit=True)
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    threading.Thread(target=worker_watchdog,daemon=True).start()
    threading.Thread(target=supervised_worker,daemon=True).start()
    print('CALIBRATION_MENU_READY',flush=True)
    server.serve_forever()
if __name__=='__main__':main()
