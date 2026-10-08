import json
from pathlib import Path
import time
import urllib.request
import psutil
ROOT=Path(__file__).resolve().parents[1]
with urllib.request.urlopen('http://127.0.0.1:8769/api/state',timeout=8) as response:state=json.load(response)
workers={}
for process in psutil.process_iter(['pid','cmdline']):
    try:
        args=process.info['cmdline'] or []
        for name,filename in [('panel','server.py'),('supervisor','assistant_supervisor.py')]:
            if str(ROOT/filename) in args:workers[name]=process.pid
    except (psutil.NoSuchProcess,psutil.AccessDenied):continue
path=ROOT/'.local/assistant-supervisor.json'
supervisor=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
report={'assistant':'Mydex','processes':workers,'supervisor_recent':path.exists() and time.time()-path.stat().st_mtime<15,
        'native_connected':state['native_sender']['connected'],'automatic_replies':state['native_sender']['enabled'],
        'web_search_enabled':state['settings']['web_search_enabled'],
        'groups':[{'name':s.get('group_name'),'running':s['running'],'model_busy':s.get('model_busy',False),
                  'last_send_error':s.get('last_send_error','')} for s in state['group_states']],
        'nickname_map_present':(ROOT/'.local/member-labels.json').exists(),
        'history_import':json.loads((ROOT/'.local/second-group-history-import.json').read_text(encoding='utf-8'))['rows_read'],
        'chat_window_required':False}
(ROOT/'.local/final-assistant-status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
