"""Exercise the local assistant API without logging private credentials."""
import argparse
import json
from pathlib import Path
import re
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8769'
def get(path):
    with urllib.request.urlopen(BASE+path,timeout=8) as response:return json.load(response)
def post(path,data):
    with urllib.request.urlopen(BASE,timeout=5) as response:html=response.read(300000).decode('utf-8')
    token=re.search(r'<meta name="lab-token" content="([^"]+)"',html).group(1)
    request=urllib.request.Request(BASE+path,json.dumps(data).encode(),
        {'Content-Type':'application/json','X-Lab-Token':token},method='POST')
    with urllib.request.urlopen(request,timeout=8) as response:return json.load(response)
parser=argparse.ArgumentParser();parser.add_argument('--send-original-summary',action='store_true')
args=parser.parse_args()
if args.send_original_summary:
    response=post('/api/native/send',{'id':'cce817e2-7a62-41e5-be1d-0391beadd36d'})
    end=time.monotonic()+45
    while time.monotonic()<end:
        result=get('/api/job?id='+response['job_id'])
        if result['status'] in ('done','error'):
            print(json.dumps(result));break
        time.sleep(.5)
    else:raise TimeoutError('Send API still working')
state=get('/api/state');native=state['native_sender'];inbox=state['database_inbox']
report={'at':time.time(),'native_sender':native,
        'group':inbox.get('group_name'),'listening':inbox['running'],
        'phase':inbox['phase'],'sending_enabled':inbox['sending_enabled'],
        'new_messages':inbox['new_messages'],'drafts':inbox['drafts'],
        'last_send_status':inbox.get('last_send_status'),
        'last_model_error':inbox.get('last_model_error',''),
        'last_send_error':inbox.get('last_send_error',''),
        'outbox_states':[{'id':d['id'],'state':d['state']} for d in state['outbox']]}
(ROOT/'.local/native-assistant-status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report))
