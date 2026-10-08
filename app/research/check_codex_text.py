"""Innocuous text-only inference diagnostic. No WeChat data or credentials."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab import codex_args,DATA
parser=argparse.ArgumentParser()
parser.add_argument('--proxy',action='store_true')
args=parser.parse_args()
environment=os.environ.copy()
if args.proxy:
    import psutil
    active=[c for c in psutil.net_connections('tcp') if c.status=='LISTEN' and c.laddr.ip=='127.0.0.1' and c.laddr.port==7890]
    if not active or not all(psutil.Process(c.pid).name().lower()=='clash-win64.exe' for c in active):
        raise ValueError('Expected existing local proxy not found')
    environment.update(HTTPS_PROXY='http://127.0.0.1:7890',HTTP_PROXY='http://127.0.0.1:7890')
command=codex_args(DATA/'codex-work')+['-c','model_reasoning_effort="low"']
started=time.monotonic()
process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=environment)
process.stdin.write('只回复：收到。'.encode('utf-8'));process.stdin.close()
for line in iter(process.stdout.readline,b''):
    print(line.decode('utf-8','replace').rstrip(),flush=True)
print(json.dumps({'exit_code':process.wait(),'seconds':round(time.monotonic()-started,2),'local_proxy':args.proxy}))
