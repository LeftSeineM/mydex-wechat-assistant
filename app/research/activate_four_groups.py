"""One verified v3-to-v4 transition for the two explicitly requested groups."""
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request
import psutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'))
from research.worker_sender_v3.run import action as old_action
from research.worker_sender_v4.run import action as new_action
from research.start_background import start
from history_reader import TargetHistory
from research.history_vfs import HistoryView
from inspect_open_databases import inventory
DATA=ROOT/'.local';BASE='http://127.0.0.1:8769'

def api(path,payload=None):
    if payload is None:
        with urllib.request.urlopen(BASE+path,timeout=8) as r:return json.load(r)
    with urllib.request.urlopen(BASE,timeout=8) as r:html=r.read().decode('utf-8')
    token=re.search(r'<meta name="lab-token" content="([^"]+)"',html).group(1)
    request=urllib.request.Request(BASE+path,json.dumps(payload).encode(),{'Content-Type':'application/json','X-Lab-Token':token},method='POST')
    with urllib.request.urlopen(request,timeout=8) as r:return json.load(r)

def stop_worker(filename):
    expected=str(ROOT/filename)
    allowed={Path(sys.executable).resolve(),Path(sys._base_executable).resolve()}
    for p in psutil.process_iter(['cmdline','exe']):
        try:
            if expected not in (p.info['cmdline'] or []):continue
            if Path(p.info['exe']).resolve() not in allowed:raise ValueError('Unexpected helper binary')
            p.terminate();p.wait(5)
        except psutil.NoSuchProcess:continue

def main():
    selected=json.loads((DATA/'new-group-selections.json').read_text(encoding='utf-8'))
    expected=[('90000000001@chatroom','AAA紫一真🈚了'),('90000000005@chatroom','示例群B')]
    if [(g['room_id'],g['name']) for g in selected]!=expected:raise ValueError('Selection changed')
    fixture=json.loads((DATA/'three-group-sender-fixture.json').read_text())
    if not fixture.get('passed') or not fixture.get('fourth_group_verified'):raise ValueError('Fixture not verified')
    config=json.loads((DATA/'native-sender-settings.json').read_text())
    pid=config['pid'];created=config['process_created']
    if psutil.Process(pid).create_time()!=created or config.get('account_verified') is not True:raise ValueError('Unverified client session')
    old=old_action(pid,'status')
    if old['phase']!=2 or not old['worker_thread']:raise ValueError('Existing native worker is not ready')
    if old['worker_thread'] not in {t.id for t in psutil.Process(pid).threads()}:raise ValueError('Existing worker thread exited')
    reader=TargetHistory();roots=set()
    for raw in inventory(pid)['database_paths']:
        for p in Path(raw).parents:
            if p.name=='db_storage':roots.add(p.parent)
    if roots!={reader.account_root}:raise ValueError('Logged in account differs')
    path=next(p for p in reader.keys if Path(p).name=='contact.db');key,salt=reader.keys[path]
    with HistoryView(path,key,salt) as view:
        for room,name in expected:
            if view.query('SELECT nick_name FROM contact WHERE username=?',(room,))!=[(name,)]:raise ValueError('Group contact changed')
    original_groups=json.loads((DATA/'monitored-groups.json').read_text(encoding='utf-8'))
    if len(original_groups)!=2:raise ValueError('Transition already applied or scope changed')
    stop_worker('assistant_supervisor.py')
    api('/api/history/stop',{});api('/api/native/sending',{'enabled':False})
    deadline=time.monotonic()+50
    while True:
        state=api('/api/state');native=old_action(pid,'status')
        busy=any(g.get('model_busy') for g in state['group_states']) or native['pending']
        busy=busy or any(d['state']=='sending' for d in state['outbox'])
        if not busy:break
        if time.monotonic()>deadline:raise TimeoutError('Existing replies still active; hooks untouched')
        time.sleep(.5)
    stop_worker('server.py')
    stopped=old_action(pid,'stop')
    if stopped['return_code'] or stopped['phase']!=5:raise ValueError('Old hooks not restored')
    installed=new_action(pid,'install')
    if installed['return_code'] or installed['phase']!=2:raise ValueError('New worker installation failed')
    if not installed['worker_thread']:
        adopted=new_action(pid,'adopt',adopt_thread=old['worker_thread'])
        if adopted['return_code']:raise ValueError('Worker adoption failed')
    native=new_action(pid,'status')
    for entry in selected:
        original_groups.append({**entry,'configured_name':entry['name'],'group_model_authorized':True,
            'history_import':False,'added_at':time.time(),'authorization':'explicit_user_screenshot_go_online'})
    (DATA/'monitored-groups.json').write_text(json.dumps(original_groups,ensure_ascii=False,indent=2),encoding='utf-8')
    config['sender_sha256']=native['sender_sha256']
    (DATA/'native-sender-settings.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    panel=start(pid,only=['panel'])
    flags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB
    with (DATA/'supervisor-v4.stdout.log').open('ab') as out,(DATA/'supervisor-v4.stderr.log').open('ab') as err:
        child=subprocess.Popen([sys.executable,'-u',str(ROOT/'assistant_supervisor.py')],cwd=ROOT,
            stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=flags,close_fds=True)
    report={'groups':[g['name'] for g in original_groups],'worker_thread_retained':native['worker_thread']==old['worker_thread'],
            'client_pid':pid,'panel':panel,'supervisor_pid':child.pid,'messages_sent':0}
    (DATA/'four-group-upgrade.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
