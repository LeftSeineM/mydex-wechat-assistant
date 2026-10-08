"""Retry only the human-confirmed recent inbound @; never sends to WeChat."""
import json,re,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
url='http://127.0.0.1:8769'
with urllib.request.urlopen(url,timeout=5) as response:
    token=re.search(r'<meta name="lab-token" content="([^"]+)"',response.read(300000).decode()).group(1)
def post(path,value):
    request=urllib.request.Request(url+path,json.dumps(value).encode(),
        {'Content-Type':'application/json','X-Lab-Token':token},method='POST')
    with urllib.request.urlopen(request,timeout=5) as response:return json.load(response)
post('/api/settings',{'codex_proxy':'http://127.0.0.1:7890'})
events=[json.loads(line) for line in (ROOT/'.local/database-group-events.jsonl').read_text(encoding='utf-8').splitlines()]
event=next(e for e in reversed(events) if e.get('mention_verified') is True and not e.get('is_self'))
job=post('/api/history/retry-at',{'id':event['id']})
start=time.monotonic()
while time.monotonic()-start<180:
    with urllib.request.urlopen(url+'/api/job?id='+job['job_id'],timeout=5) as response:state=json.load(response)
    if state['status'] in ('done','error'):
        result=state.get('result',{})
        report={'job_status':state['status'],'seconds':round(time.monotonic()-start,2),
                'event_id':event['id'],'result_status':result.get('status'),'draft_id':result.get('draft_id'),
                'reply_chars':len(result.get('reply','')),'error':state.get('error'),
                'sent_to_wechat':False,'record_scope':result.get('record_scope')}
        if result.get('reply'):
            (ROOT/'.local/group-summary.txt').write_text(result['reply'],encoding='utf-8')
        (ROOT/'.local/group-summary-status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False));break
    time.sleep(1)
else:raise TimeoutError('Local summary job still running')
