"""Local photo/video frame; USB is a read-only source."""
import hmac, hashlib, json, os, re, shutil, stat, subprocess, threading, tempfile, queue, time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
ALBUM=Path.home()/'rs-family-photos'
USB=Path('__RS_FAMILY_USB_PATH__')
CACHE=Path.home()/'.cache/rs-family-frame'
HOST='__RS_BRIDGE_HOST__'
TV='__RS_TV_HOST__'
LIMIT=12*1024*1024
TYPES={'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.mp4':'video/mp4'}
lock=threading.Lock()
meta_lock=threading.RLock()
EDIT_KEY='__RS_FRAME_KEY__'
STATE=Path.home()/'.config/rs-family-frame/frame-state.json'

def metadata():
    if not STATE.exists():return {"rotations":{}, "hidden":[]}
    fd=os.open(STATE,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd) as f:
        st=os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o077:
            raise OSError("unsafe metadata")
        data=json.load(f)
    if not isinstance(data.get("rotations"),dict) or not isinstance(data.get("hidden"),list):
        raise ValueError("invalid metadata")
    return data

def save_metadata(data):
    STATE.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=STATE.parent,prefix=".frame-")
    try:
        with os.fdopen(fd,"w") as f:
            json.dump(data,f,separators=(",",":"));f.flush();os.fsync(f.fileno())
        os.replace(tmp,STATE)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def edit(data,body,available):
    op=body.get("op")
    if op=="restore":
        if not data["hidden"]:return False
        data["hidden"].pop();return True
    key=body.get("id")
    if not isinstance(key,str) or key not in available:return False
    if op=="hide":
        if key not in data["hidden"]:data["hidden"].append(key)
        return True
    if op=="rotate":
        value=body.get("rotation")
        if type(value) is not int or value not in (0,90,180,270):return False
        if value:data["rotations"][key]=value
        else:data["rotations"].pop(key,None)
        return True
    return False


def volume_generation(root):
    """Identify a mounted volume, not just its mount path.

    The kernel mount ID changes on unplug/reinsert and when a different flash
    drive is mounted at the same directory. Avoid retaining a stale playlist
    when the replacement carries identical file names and timestamps.
    """
    try:
        target=str(root.resolve())
        with open('/proc/self/mountinfo',encoding='utf-8') as src:
            for line in src:
                fields=line.split()
                if len(fields)>5 and fields[4].replace(r'\040',' ')==target:
                    return fields[0]
    except OSError:
        pass
    try:
        stat_root=root.stat()
        return str(stat_root.st_dev)+':'+str(stat_root.st_ino)
    except OSError:
        return 'missing'


def entry_revision(p,s,volume):
    """Tiny opaque revision: file replacement, edit and drive changes."""
    payload=(str(s.st_dev)+':'+str(s.st_ino)+':'+str(s.st_size)+':'
             +str(s.st_mtime_ns)+':'+str(volume))
    return hashlib.sha256(payload.encode('ascii')).hexdigest()[:16]


def media_paths(root):
    """Read changing folders without following symlinks or leaving the volume.

    A replacement flash drive can contain its own DCIM, Photos and Videos
    folders. Limit traversal to bound work on Raspberry Pi 3.
    """
    try:root_device=root.stat().st_dev
    except OSError:return
    stack=[(root,0)]
    visited=0
    while stack and visited<300:
        current,depth=stack.pop()
        visited+=1
        try:children=sorted(current.iterdir(),key=lambda p:p.name.casefold())
        except OSError:continue
        folders=[]
        for p in children:
            if p.name.startswith('.'):continue
            try:
                if p.is_symlink():continue
                s=p.stat()
            except OSError:continue
            if s.st_dev!=root_device:continue
            if stat.S_ISDIR(s.st_mode):
                if depth<4:folders.append((p,depth+1))
            elif stat.S_ISREG(s.st_mode):
                yield p,s
        stack.extend(reversed(folders))


def entries():
    result={}
    for root in (ALBUM,USB):
        if not root.is_dir() or root.is_symlink():continue
        volume=volume_generation(root)
        for p,s in media_paths(root):
            kind=TYPES.get(p.suffix.lower())
            if not kind or s.st_size<=0:continue
            if root==ALBUM and kind.startswith('image') and s.st_size>LIMIT:continue
            key=hashlib.sha256(os.fsencode(p) if root==USB else str(p.relative_to(root)).encode()).hexdigest()[:24]
            result[key]=(p,kind,entry_revision(p,s,volume))
            if len(result)>=2000:return result
    return result

VIDEO_CACHE=CACHE/'video'
video_jobs=queue.Queue(maxsize=8)
video_queued=set()
video_queued_lock=threading.Lock()
video_failures={}

def media_cache_fingerprint(p):
    """Keep private cached media distinct across swapped USB drives.

    FAT timestamps and names can coincide across drives. Sample start, middle
    and end of the source without reading multi-GB files on Raspberry Pi 3.
    """
    s=p.stat()
    hasher=hashlib.sha256(os.fsencode(p)+str((s.st_size,s.st_mtime_ns)).encode())
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as file:
        current=os.fstat(file.fileno())
        if not stat.S_ISREG(current.st_mode) or current.st_size!=s.st_size:
            raise OSError('media changed during cache fingerprint')
        offsets=sorted({0,max(0,s.st_size//2-16384),max(0,s.st_size-32768)})
        for offset in offsets:
            file.seek(offset)
            hasher.update(file.read(32768))
    return hasher.hexdigest()


def video_cache_path(p):
    return VIDEO_CACHE/(media_cache_fingerprint(p)+'.mp4')

def video_cache_ready(out):
    try:
        if out.is_symlink() or out.stat().st_size<1024:return False
        with out.open('rb') as f:head=f.read(1048576)
        return head[4:8]==b'ftyp' and b'moov' in head
    except OSError:return False

def prepare_video(p):
    if not (p.is_relative_to(USB) or p.is_relative_to(ALBUM)) or p.suffix.lower()!='.mp4' or p.is_symlink():
        raise ValueError('unsafe source')
    out=video_cache_path(p)
    if video_cache_ready(out):return out
    if shutil.disk_usage(CACHE).free<4*1024**3:
        raise OSError('not enough disk for video cache')
    VIDEO_CACHE.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.video-',suffix='.mp4',dir=VIDEO_CACHE)
    os.close(fd)
    try:
        subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-threads','1',
            '-i',str(p),'-map','0:v:0','-map','0:a:0?','-c','copy','-movflags','+faststart',
            '-map_metadata','-1','-y',tmp],check=True,timeout=120,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if not video_cache_ready(Path(tmp)):raise OSError('invalid faststart output')
        os.replace(tmp,out)
        return out
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def queue_video(p):
    try:
        dest=video_cache_path(p)
        if video_cache_ready(dest):return dest
    except OSError:return p
    with video_queued_lock:
        if dest not in video_queued and time.monotonic()-video_failures.get(dest,-1e9)>600:
            try:
                video_jobs.put_nowait((p,dest))
                video_queued.add(dest)
            except queue.Full:pass
    return p

def video_cache_worker():
    while True:
        p,dest=video_jobs.get()
        try:prepare_video(p)
        except (OSError,ValueError,subprocess.SubprocessError):
            with video_queued_lock:video_failures[dest]=time.monotonic()
        finally:
            with video_queued_lock:video_queued.discard(dest)
            video_jobs.task_done()

def photo(p):
    if not p.is_relative_to(USB):return p,TYPES[p.suffix.lower()]
    name=media_cache_fingerprint(p)
    out=CACHE/(name+'.jpg')
    with lock:
        if not out.is_file():
            CACHE.mkdir(mode=0o700,parents=True,exist_ok=True)
            if shutil.disk_usage(CACHE).free<500*1024*1024:raise OSError('cache full')
            fd,tmp=tempfile.mkstemp(suffix='.jpg',dir=CACHE);os.close(fd)
            try:
                subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-i',str(p),'-frames:v','1','-vf','scale=w=1920:h=1080:force_original_aspect_ratio=decrease','-filter_threads','1','-threads','1','-q:v','3','-map_metadata','-1','-y',tmp],check=True,timeout=35,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                if not 0<os.stat(tmp).st_size<=LIMIT:raise OSError('invalid image')
                os.replace(tmp,out)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
    return out,'image/jpeg'

class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):
        pass  # No private album IDs or network identifiers in logs.
    def do_HEAD(self):self.serve(False)
    def do_GET(self):self.serve(True)
    def headers_for(self,code,ctype,n,extra=None):
        self.send_response(code)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(n))
        self.send_header('Cache-Control','no-store')
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('X-Content-Type-Options','nosniff')
        for k,v in (extra or {}).items():self.send_header(k,v)
        self.end_headers()
    def do_POST(self):
        if self.path!='/api/edit' or self.client_address[0]!=TV:
            self.send_error(403);return
        self.connection.settimeout(8)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if self.headers.get('Transfer-Encoding') or not 0<size<=2048 or not self.headers.get('Content-Type','').startswith('text/plain'):
                self.send_error(400);return
            b=json.loads(self.rfile.read(size))
            if not isinstance(b,dict):self.send_error(400);return
            key=b.get('key')
            if not isinstance(key,str) or not key.isascii() or not hmac.compare_digest(key,EDIT_KEY):
                self.send_error(403);return
            with meta_lock:
                data=metadata()
                if not edit(data,b,entries()):self.send_error(400);return
                save_metadata(data)
                out=json.dumps({"ok":True,"hiddenCount":len(data["hidden"])}).encode()
            self.headers_for(200,'application/json',len(out));self.wfile.write(out)
        except (OSError,ValueError,TypeError):self.send_error(503)
    def serve(self,body):
        if self.client_address[0] not in (TV,HOST,'127.0.0.1'):
            self.send_error(403);return
        try:
            if self.path=='/api/album':
                with meta_lock:
                    data=metadata()
                e={k:v for k,v in entries().items() if k not in set(data['hidden'])}
                b=json.dumps({'photos':[k for k,(_,t,_) in e.items() if t.startswith('image')],'items':[{'id':k,'type':'video' if t.startswith('video') else 'photo','rotation':data['rotations'].get(k,0),'rev':rev} for k,(_,t,rev) in e.items()],'interval':10,'hiddenCount':len(data['hidden'])}).encode()
                self.headers_for(200,'application/json',len(b))
                if body:self.wfile.write(b)
                return
            match=re.fullmatch(r'/(photo|video)/([0-9a-f]{24})',self.path)
            if not match:self.send_error(404);return
            p,kind,_=entries().get(match[2],(None,None,None))
            if p is None or (match[1]=='video')!=(kind=='video/mp4'):
                self.send_error(404);return
            if match[1]=='video':p=queue_video(p)
            if match[1]=='photo':
                try:p,kind=photo(p)
                except (OSError,subprocess.SubprocessError):self.send_error(422);return
            with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as f:
                s=os.fstat(f.fileno());size=s.st_size
                if not stat.S_ISREG(s.st_mode) or size<=0:self.send_error(404);return
                start,end=0,size-1
                extra={'Accept-Ranges':'bytes'}
                r=self.headers.get('Range')
                if r:
                    m=re.fullmatch(r'bytes=(\d*)-(\d*)',r.strip())
                    valid=bool(m and (m[1] or m[2]))
                    if valid:
                        if not m[1]:start=max(0,size-int(m[2]))
                        else:
                            start=int(m[1])
                            if m[2]:end=min(end,int(m[2]))
                        valid=start<=end and start<size
                    if not valid:
                        extra['Content-Range']='bytes */%d'%size
                        self.headers_for(416,kind,0,extra);return
                    extra['Content-Range']='bytes %d-%d/%d'%(start,end,size)
                remaining=end-start+1
                self.headers_for(206 if r else 200,kind,remaining,extra)
                if body:
                    f.seek(start)
                    while remaining:
                        data=f.read(min(remaining,65536))
                        if not data:break
                        self.wfile.write(data);remaining-=len(data)
        except (OSError,ValueError):return
if __name__=='__main__':
    os.umask(0o077)
    ALBUM.mkdir(mode=0o700,exist_ok=True)
    threading.Thread(target=video_cache_worker,daemon=True,name="video-cache").start()
    ThreadingHTTPServer((HOST,8788),Handler).serve_forever()
