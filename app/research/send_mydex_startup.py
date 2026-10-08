"""The human-requested startup phrase, to the newly selected group only."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from history_reader import TargetHistory
from research.worker_sender_v3.run import action
TEXT='Mydex：\n🟢 我是群研究助手Mydex，已上线。\n\n用微信成员选择功能 @示例账号 提问，我会在本群回答。\n支持：讨论总结 · 待办整理 · 问题解答。'
room='90000000006@chatroom'
reader=TargetHistory(group="示例朋友群")
cursors={p:reader.fetch(p,reader.name)['cursor'] for p in reader.message_paths()}
result=action(55832,'send',TEXT,room=room)
if result['return_code']:raise ValueError('Startup phrase was not queued')
end=time.monotonic()+20;matches=[]
while time.monotonic()<end:
    for path,cursor in cursors.items():
        events=reader.fetch(path,reader.name,cursor)['events']
        matches=[{'id':e['id'],'created':e['created']} for e in events if e.get('is_self') and e['content']==TEXT
                 and e['id'].isdigit() and int(e['id'])]
        if matches:break
    if matches:break
    time.sleep(.4)
report={'startup_phrase':'我是群研究助手Mydex','group':reader.name,'server_record_verified':bool(matches),'messages':matches}
(ROOT/'.local/mydex-startup-proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
