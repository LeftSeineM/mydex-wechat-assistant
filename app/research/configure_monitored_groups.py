"""Persist the two groups explicitly selected by the user, not other chats."""
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
binding=json.loads((ROOT/'.local/group-binding.json').read_text(encoding='utf-8'))
rows=json.loads((ROOT/'.local/requested-group-candidates.json').read_text(encoding='utf-8'))
if rows!=[{'room_id':'90000000006@chatroom','name':"示例朋友群"}]:raise ValueError('Selected group differs')
groups=[{'room_id':binding['room_id'],'name':binding['group_name'],
         'configured_name':'示例工作群','group_model_authorized':True,'history_import':True},
        {'room_id':rows[0]['room_id'],'name':rows[0]['name'],'configured_name':rows[0]['name'],
         'group_model_authorized':True,'history_import':False,'authorization':'explicit_user_add_this_group'}]
(ROOT/'.local/monitored-groups.json').write_text(json.dumps(groups,ensure_ascii=False,indent=2),encoding='utf-8')
base='http://127.0.0.1:8769'
with urllib.request.urlopen(base,timeout=5) as r:html=r.read(300000).decode('utf-8')
token=re.search(r'<meta name="lab-token" content="([^"]+)"',html).group(1)
request=urllib.request.Request(base+'/api/settings',json.dumps({'bot_name':'M'}).encode(),
                              {'Content-Type':'application/json','X-Lab-Token':token},method='POST')
with urllib.request.urlopen(request,timeout=5) as r:cfg=json.load(r)
if cfg['bot_name']!='M':raise ValueError('Reply prefix not applied')
print(json.dumps({'prefix':'M：','groups':[g['name'] for g in groups]},ensure_ascii=False))
