"""Reload Python helpers after replies finish; leave the WeChat bridge intact."""
import json
from pathlib import Path
import re
import subprocess
import sqlite3
import sys
import time
import urllib.request
import psutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'))
from start_background import start
DATA=ROOT/'.local';BASE='http://127.0.0.1:8769'

def api(path,payload=None):
    if payload is None:
        with urllib.request.urlopen(BASE+path,timeout=15) as response:return json.load(response)
    with urllib.request.urlopen(BASE,timeout=10) as response:html=response.read().decode()
    token=re.search(r'<meta name="lab-token" content="([^"]+)"',html).group(1)
    req=urllib.request.Request(BASE+path,json.dumps(payload).encode(),
        {'Content-Type':'application/json','X-Lab-Token':token},method='POST')
    with urllib.request.urlopen(req,timeout=15) as response:return json.load(response)

def stop_supervisor():
    expected=str(ROOT/'assistant_supervisor.py')
    allowed={Path(sys.executable).resolve(),Path(sys._base_executable).resolve()}
    for proc in psutil.process_iter(['exe','cmdline']):
        try:
            if expected not in (proc.info['cmdline'] or []):continue
            if Path(proc.info['exe']).resolve() not in allowed:raise ValueError('Unexpected worker')
            proc.terminate();proc.wait(5)
        except psutil.NoSuchProcess:pass

def start_supervisor():
    flags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB
    with (DATA/'supervisor-latency.stdout.log').open('ab') as out,(DATA/'supervisor-latency.stderr.log').open('ab') as err:
        return subprocess.Popen([sys.executable,'-u',str(ROOT/'assistant_supervisor.py')],cwd=ROOT,
            stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=flags,close_fds=True).pid

def main():
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        states=[json.loads(p.read_text(encoding='utf-8')) for p in DATA.glob('database-inbox*.json')]
        if any(s.get('model_busy') for s in states):time.sleep(1);continue
        # The old full state endpoint is slow enough to miss a short idle
        # window. Its persisted statuses and local outbox suffice here.
        with sqlite3.connect((DATA/'history.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
            if db.execute("SELECT 1 FROM outbox WHERE state='sending' LIMIT 1").fetchone():continue
        # Stop new intake only after the current model/send workers are idle.
        api('/api/history/stop',{})
        time.sleep(1)
        state=api('/api/state')
        if any(s.get('model_busy') for s in state['group_states']):
            api('/api/history/start',{})
            raise RuntimeError('A reply started during the idle check; reload deferred')
        stop_supervisor()
        try:
            config=json.loads((DATA/'native-sender-settings.json').read_text())
            if psutil.Process(config['pid']).create_time()!=config['process_created']:
                raise ValueError('Client session changed')
            result=start(config['pid'],reload=['panel'],only=['panel'])
        finally:
            supervisor_pid=start_supervisor()
        for attempt in range(30):
            try:
                health=api('/api/health')
                if health.get('service')=='wechat-group-lab':
                    result={'panel':result,'supervisor_pid':supervisor_pid,'health':health,'model':'gpt-6-luna'}
                    (DATA/'latency-update-deployment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
                    print(json.dumps({'deployed':True,'groups':len(health['groups'])}),flush=True);return
            except OSError:pass
            time.sleep(1)
        raise RuntimeError('Panel health not confirmed')
    print(json.dumps({'deployed':False,'reason':'Replies still active; model settings already live'}),flush=True)

if __name__=='__main__':main()
