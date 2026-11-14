"""Local photo/video frame; USB is a read-only source."""
import hashlib, json, os, re, shutil, stat, subprocess, threading, tempfile
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

def entries():
    result={}
    for root in (ALBUM,USB):
        if not root.is_dir() or root.is_symlink():continue
        for p in sorted(root.iterdir(),key=lambda p:p.name.casefold()):
            kind=TYPES.get(p.suffix.lower())
            if p.name.startswith('.') or not kind or p.is_symlink():continue
            try:s=p.stat()
            except OSError:continue
            if not stat.S_ISREG(s.st_mode) or s.st_size<=0:continue
            if root==ALBUM and kind.startswith('image') and s.st_size>LIMIT:continue
            key=hashlib.sha256(os.fsencode(p) if root==USB else p.name.encode()).hexdigest()[:24]
            result[key]=(p,kind)
            if len(result)>=2000:return result
    return result

def photo(p):
    if p.parent!=USB:return p,TYPES[p.suffix.lower()]
    s=p.stat()
    name=hashlib.sha256(os.fsencode(p)+str((s.st_size,s.st_mtime_ns)).encode()).hexdigest()
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
        print(self.client_address[0],fmt%args,flush=True)
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
    def serve(self,body):
        if self.client_address[0] not in (TV,HOST,'127.0.0.1'):
            self.send_error(403);return
        try:
            if self.path=='/api/album':
                e=entries()
                b=json.dumps({'photos':[k for k,(_,t) in e.items() if t.startswith('image')],'items':[{'id':k,'type':'video' if t.startswith('video') else 'photo'} for k,(_,t) in e.items()],'interval':10}).encode()
                self.headers_for(200,'application/json',len(b))
                if body:self.wfile.write(b)
                return
            match=re.fullmatch(r'/(photo|video)/([0-9a-f]{24})',self.path)
            if not match:self.send_error(404);return
            p,kind=entries().get(match[2],(None,None))
            if p is None or (match[1]=='video')!=(kind=='video/mp4'):
                self.send_error(404);return
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
    ThreadingHTTPServer((HOST,8788),Handler).serve_forever()
