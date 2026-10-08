"""Cleanly replace v2 with the tested two-group worker, retaining its thread."""
import json
from pathlib import Path
import re
import sqlite3
import sys
import time
import urllib.request
import psutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.worker_sender_v2.run import action as old_action
from research.worker_sender_v3.run import action as new_action
from research.start_background import start
pid=55832
base='http://127.0.0.1:8769'
with urllib.request.urlopen(base,timeout=5) as r:html=r.read(300000).decode('utf-8')
token=re.search(r'<meta name="lab-token" content="([^"]+)"',html).group(1)
request=urllib.request.Request(base+'/api/history/stop',b'{}',{'Content-Type':'application/json','X-Lab-Token':token},method='POST')
with urllib.request.urlopen(request,timeout=5) as r:json.load(r)
end=time.monotonic()+45
while True:
    model_busy=False
    for process in psutil.process_iter(['name','cmdline']):
        try:
            args=process.info['cmdline'] or []
            if (process.info['name'] or '').lower()=='codex.exe' and '--ignore-user-config' in args and '--ephemeral' in args:model_busy=True
        except (psutil.NoSuchProcess,psutil.AccessDenied):continue
    db=sqlite3.connect(ROOT/'.local/history.sqlite3')
    sending=db.execute('SELECT COUNT(*) FROM outbox WHERE state=?',('sending',)).fetchone()[0];db.close()
    old=old_action(pid,'status')
    if not sending and not model_busy and old['pending']==0:break
    if time.monotonic()>end:raise TimeoutError('Existing reply still active; no native hooks changed')
    time.sleep(.5)
if old['phase']!=2 or not old['worker_thread']:raise ValueError('Existing worker not verified')
thread=old['worker_thread']
stopped=old_action(pid,'stop')
if stopped['return_code'] or stopped['phase']!=5:raise ValueError('Old hooks did not restore')
new=new_action(pid,'install')
if new['return_code'] or new['phase']!=2:raise ValueError('New hooks did not install')
if not new['worker_thread']:
    adopted=new_action(pid,'adopt',adopt_thread=thread)
    if adopted['return_code']:raise ValueError('Verified worker was not adopted')
status=new_action(pid,'status')
config=json.loads((ROOT/'.local/native-sender-settings.json').read_text(encoding='utf-8'))
config.update(pid=pid,enabled=True,sender_sha256=status['sender_sha256'],process_created=psutil.Process(pid).create_time())
(ROOT/'.local/native-sender-settings.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
launched=start(pid,reload=['panel'],only=['panel'])
print(json.dumps({'old_hooks_stopped':True,'new_worker_ready':bool(status['worker_thread']),
                  'pid':pid,'panel':launched['panel'],'two_groups_enabled':True}))
