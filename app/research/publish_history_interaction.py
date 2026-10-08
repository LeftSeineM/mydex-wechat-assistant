"""Publish the reviewed, user-requested old-topic interaction to its own group."""
import json
from pathlib import Path
import sqlite3
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from history_reader import TargetHistory
from research.worker_sender_v3.run import action
draft=json.loads((ROOT/'.local/history-interaction-draft.json').read_text(encoding='utf-8'))
if draft['group']!="示例朋友群" or not draft['grounded_in_target_group_history'] or draft['sent']:
    raise ValueError('Interaction scope or state differs')
db=sqlite3.connect(ROOT/'.local/history.sqlite3')
support=[]
for topic in ('PPT','公众号'):
    rows=db.execute('SELECT event_id FROM messages WHERE source=? AND room=? AND message_time<? AND content LIKE ?',
                    ('wechat',draft['group'],draft['old_records_before'],'%'+topic+'%')).fetchall()
    if not any(row[0] in draft['source_ids'] for row in rows):raise ValueError('Topic evidence missing')
    support.append(topic)
db.close()
TEXT='Mydex：\n补充一下：联网查公开资料已可用，称呼也会优先用群昵称。\n\n'+draft['reply']
reader=TargetHistory(group=draft['group'])
cursors={p:reader.fetch(p,reader.name)['cursor'] for p in reader.message_paths()}
queued=action(55832,'send',TEXT,room=reader.room)
if queued['return_code']:raise ValueError('Interaction not queued')
found=[];end=time.monotonic()+20
while time.monotonic()<end:
    for path,cursor in cursors.items():
        events=reader.fetch(path,reader.name,cursor)['events']
        found=[e['id'] for e in events if e['content']==TEXT and e.get('is_self') and e['id'].isdigit() and int(e['id'])]
        if found:break
    if found:break
    time.sleep(.4)
draft.update(sent=bool(found),server_record_verified=bool(found),reply_ids=found,corroborated_topics=support)
(ROOT/'.local/history-interaction-draft.json').write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'group':reader.name,'server_record_verified':bool(found),'reply_ids':found,'interaction':draft['reply']},ensure_ascii=False))
