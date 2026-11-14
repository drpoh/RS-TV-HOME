"""Run manually on Pi; code is never printed or stored in plaintext."""
import getpass,hashlib,json,os,secrets,sys
from pathlib import Path
if not sys.stdin.isatty():raise SystemExit('Use your own terminal.')
os.umask(0o077)
p=Path.home()/'.config/rs-family-frame'
p.mkdir(mode=0o700,parents=True,exist_ok=True)
key=getpass.getpass('New 4-digit album PIN: ')
if len(key)!=4 or not key.isascii() or not key.isdigit():raise SystemExit('Use exactly four digits.')
if key!=getpass.getpass('Repeat PIN: '):raise SystemExit('Codes differ.')
salt=secrets.token_bytes(16)
result={'salt':salt.hex(),'hash':hashlib.scrypt(key.encode(),salt=salt,n=16384,r=8,p=1).hex()}
tmp=p/'upload-auth.new'
fd=os.open(tmp,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w') as f:json.dump(result,f)
os.replace(tmp,p/'upload-auth.json')
print('Album PIN configured.')
