"""Enable only the human-requested fixed-group native assistant."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab import Settings, Store
from research.worker_sender_v2.run import action

pid=55832
live=action(pid,'status')
proof=json.loads((ROOT/'.local/native-delivery-proof.json').read_text(encoding='utf-8'))
if not (live['phase']==2 and live['worker_thread'] and live['context_failures']==0
        and proof.get('server_record_verified') and proof.get('native_delivery_verified')):
    raise ValueError('Real send not verified')
binding=json.loads((ROOT/'.local/group-binding.json').read_text(encoding='utf-8'))
if binding['room_id']!='90000000003@chatroom':raise ValueError('Wrong group')
event_id='6029702332957067462'
key='cce817e2-7a62-41e5-be1d-0391beadd36d'
events=[json.loads(line) for line in (ROOT/'.local/database-group-events.jsonl').read_text(encoding='utf-8').splitlines()]
event=next(e for e in events if e.get('id')==event_id)
if event.get('room_id')!=binding['room_id'] or event.get('mention_verified') is not True or event.get('is_self'):
    raise ValueError('Original mention not verified')
store=Store()
try:
    row=store.db.execute('SELECT * FROM outbox WHERE id=?',(key,)).fetchone()
    assistant=store.db.execute('SELECT content FROM messages WHERE source=? AND room=? AND role=? AND event_id=?',
                               ('wechat',event['room'],'assistant',event_id)).fetchone()
    if not row or not assistant or row['content']!=assistant['content'] or row['room']!=event['room']:
        raise ValueError('Original summary not linked')
    store.db.execute('UPDATE outbox SET source=?,event_id=? WHERE id=?',('wechat',event_id,key));store.db.commit()
finally:store.db.close()
Settings().update({'max_reply_chars':900})
(ROOT/'.local/native-sender-settings.json').write_text(json.dumps({'enabled':True,'pid':pid,
    'group_id':binding['room_id'],'at':datetime.now(timezone.utc).isoformat(),
    'source':'explicit_human_request_fixed_group_auto_replies',
    'sender_sha256':live['sender_sha256']},indent=2),encoding='utf-8')
print(json.dumps({'automatic_replies_enabled':True,'pid':pid,'original_summary_draft_linked':True}))
