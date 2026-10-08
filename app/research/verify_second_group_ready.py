import json
from pathlib import Path
import sys
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from history_reader import TargetHistory
from research.worker_sender_v3.run import action
TEXT='M：🟢 群助手已上线。用微信成员选择功能 @示例账号 提问，我会在本群回答；也可以让我总结讨论、整理待办。'
reader=TargetHistory(group="示例朋友群")
end=time.monotonic()+15
found=[]
while time.monotonic()<end:
    for path in reader.message_paths():
        result=reader.fetch(path,reader.name)
        found+=[{'id':e['id'],'created':e['created']} for e in result['events'] if e['content']==TEXT
                and e.get('is_self') and e['id'].isdigit() and int(e['id'])]
    if found:break
    time.sleep(.5)
with urllib.request.urlopen('http://127.0.0.1:8769/api/state',timeout=6) as response:state=json.load(response)
live=action(55832,'status')
draft=next((d for d in state['outbox'] if d['room']==reader.name and d['state']=='sent'),None)
report={'group':reader.name,'announcement_server_verified':bool(found),'announcement':found,
        'prefix':state['settings']['bot_name'],'native_sender':state['native_sender'],
        'native_executed':live['executed'],'native_context_failures':live['context_failures'],
        'latest_auto_reply': {'content':draft['content'],'draft_id':draft['id'],'request_id':draft['event_id']} if draft else None,
        'groups':[{'name':s.get('group_name'),'running':s['running'],'phase':s['phase'],
                   'sending_enabled':s['sending_enabled'],'drafts':s['drafts'],
                   'last_model_error':s.get('last_model_error',''),'last_send_error':s.get('last_send_error','')} for s in state['group_states']]}
(ROOT/'.local/second-group-ready.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
