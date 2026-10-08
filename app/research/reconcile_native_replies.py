"""Resolve interrupted verification only from server-backed target-group rows.
Never submits or resubmits any native send.
"""
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from history_reader import TargetHistory
from lab import Settings
reader=TargetHistory();cfg=Settings().get()
if cfg['group'] not in reader.aliases or reader.room!='90000000003@chatroom':raise ValueError('Wrong group')
db=sqlite3.connect(ROOT/'.local/history.sqlite3');db.row_factory=sqlite3.Row
try:
    candidates=db.execute('SELECT * FROM outbox WHERE source=? AND room=? AND state=?',
                          ('wechat',cfg['group'],'unknown')).fetchall()
    events=[]
    if candidates:
        for path in reader.message_paths():events+=reader.fetch(path,cfg['group'])['events']
    incoming=[json.loads(line) for line in (ROOT/'.local/database-group-events.jsonl').read_text(encoding='utf-8').splitlines()]
    confirmed=[]
    for draft in candidates:
        linked=db.execute('SELECT 1 FROM messages WHERE source=? AND room=? AND role=? AND event_id=? AND content=?',
                           ('wechat',cfg['group'],'assistant',draft['event_id'],draft['content'])).fetchone()
        if not linked:continue
        body=cfg['bot_name']+'：\n'+draft['content']
        matches=[e for e in events if e.get('is_self') is True and e['content']==body
                 and draft['created']-5 <= e['created'] <= draft['created']+120
                 and e['id'].isdigit() and int(e['id'])]
        if len(matches)!=1:continue
        event=matches[0]
        request=next((e for e in incoming if e['id']==draft['event_id']),{})
        proof={'at':datetime.now(timezone.utc).isoformat(),'draft_id':draft['id'],
               'request_event_id':draft['event_id'],'reply_event_id':event['id'],
               'room_id':reader.room,'group':reader.name,'server_record_verified':True,
               'request_mention_verified':request.get('mention_verified') is True,
               'request_from_other_member':request.get('is_self') is False,
               'reply':draft['content'],'reply_seconds_after_request':event['created']-request['created'] if request else None,
               'reconciled_after_service_reload':True,'messages_resent':0}
        db.execute('UPDATE outbox SET state=? WHERE id=? AND state=?',('sent',draft['id'],'unknown'))
        db.commit();confirmed.append(proof)
        (ROOT/'.local/native-reply-delivery.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'confirmed':confirmed,'messages_resent':0}))
finally:db.close()
