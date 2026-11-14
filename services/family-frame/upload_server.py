"""Authenticated, LAN-only photo ingestion. No read/list/delete API."""
import hashlib,hmac,ipaddress,json,os,secrets,shutil,socket,stat,subprocess,tempfile,threading,time
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
from server import ALBUM,HOST,LIMIT
ROOT=Path(__file__).resolve().parent
AUTH=Path.home()/'.config/rs-family-frame/upload-auth.json'
NETWORK=ipaddress.ip_network('__RS_FAMILY_NETWORK__')
ATTEMPTS={}
def configured():
    s=AUTH.stat()
    if not stat.S_ISREG(s.st_mode) or s.st_mode&0o077 or s.st_uid!=os.getuid():raise OSError('unsafe auth file')
    return json.loads(AUTH.read_text())
def check_key(key,data):
    if len(key)!=4 or not key.isascii() or not key.isdigit():return False
    digest=hashlib.scrypt(key.encode(),salt=bytes.fromhex(data['salt']),n=16384,r=8,p=1)
    return hmac.compare_digest(digest.hex(),data['hash'])
def convert(raw,output):
    if raw[:3]!=b'\xff\xd8\xff' and raw[:8]!=b'\x89PNG\r\n\x1a\n':return False
    # Use one decoder thread, enforce memory ceiling per allocation and bounded runtime.
    r=subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-max_alloc','67108864','-threads','1','-i','pipe:0','-frames:v','1','-vf','scale=1920:1080:force_original_aspect_ratio=decrease','-map_metadata','-1','-threads','1','-q:v','3','-f','image2','-y',str(output)],input=raw,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=25)
    return r.returncode==0 and output.is_file() and 0<output.stat().st_size<=LIMIT
class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(12)
    def log_message(self,*args):pass
    def respond(self,code,body=None,typ='application/json'):
        b=(json.dumps(body or {}).encode() if typ=='application/json' else body)
        self.send_response(code);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(b)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers();self.wfile.write(b)
    def allowed(self):
        return ipaddress.ip_address(self.client_address[0]) in NETWORK
    def do_GET(self):
        if not self.allowed():return self.respond(403)
        if self.path!='/':return self.respond(404)
        self.respond(200,(ROOT/'upload.html').read_bytes(),'text/html; charset=utf-8')
    def do_POST(self):
        if not self.allowed():return self.respond(403)
        if self.path!='/api/upload':return self.respond(404)
        if self.headers.get('Transfer-Encoding'):return self.respond(400)
        ip=self.client_address[0];now=time.monotonic()
        # Single-worker server plus per-IP 5 failed attempts per five minutes.
        bad=[t for t in ATTEMPTS.get(ip,[]) if now-t<300]
        if len(bad)>=5:return self.respond(429)
        try:data=configured()
        except (OSError,ValueError):return self.respond(503)
        try:valid=check_key(self.headers.get('X-Album-Key',''),data)
        except (ValueError,KeyError):return self.respond(503)
        if not valid:
            ATTEMPTS[ip]=bad+[now];return self.respond(401)
        ATTEMPTS.pop(ip,None)
        try:n=int(self.headers.get('Content-Length','0'))
        except ValueError:return self.respond(400)
        if not 0<n<=LIMIT:return self.respond(413)
        if sum(1 for p in ALBUM.iterdir() if p.is_file() and p.suffix.lower() in ('.jpg','.jpeg','.png'))>=1000:return self.respond(507)
        if shutil.disk_usage(ALBUM).free<500*1024*1024:return self.respond(507)
        try:raw=self.rfile.read(n)
        except (TimeoutError,OSError):return
        if len(raw)!=n:return self.respond(400)
        name=time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(8)
        temp=ALBUM/('.upload-'+name+'.jpg')
        try:
            if not convert(raw,temp):return self.respond(422)
            os.chmod(temp,0o600);os.replace(temp,ALBUM/(name+'.jpg'))
            self.respond(201,{'ok':True})
        except (OSError,subprocess.TimeoutExpired):self.respond(422)
        finally:temp.unlink(missing_ok=True)
if __name__=='__main__':
    os.umask(0o077);ALBUM.mkdir(mode=0o700,exist_ok=True)
    HTTPServer((HOST,8789),Handler).serve_forever()
