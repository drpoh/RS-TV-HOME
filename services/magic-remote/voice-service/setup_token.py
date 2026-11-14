"""Run locally on Pi; never paste a token into chat."""
import getpass,os,sys
from pathlib import Path
if not sys.stdin.isatty():raise SystemExit('Use your own interactive terminal.')
os.umask(0o077)
p=Path.home()/'.config/rs-magic-voice'
p.mkdir(parents=True, mode=0o700,exist_ok=True)
token=getpass.getpass('Home Assistant access token: ').strip()
if len(token)<20:raise SystemExit('Token missing or too short')
tmp=p/'token.new'
fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w') as f:f.write(token+'\n')
os.replace(tmp,p/'token')
print('Token saved locally, mode 0600.')
