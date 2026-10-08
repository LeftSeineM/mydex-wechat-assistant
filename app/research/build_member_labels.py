"""Public nicknames only for participants in the two authorized groups."""
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from history_reader import TargetHistory
from research.history_vfs import HistoryView
from member_labels import group_nicknames
from group_scopes import scopes
from lab import Settings
reader=TargetHistory();path=next(p for p in reader.keys if Path(p).name=='contact.db');key,salt=reader.keys[path]
db=sqlite3.connect(ROOT/'.local/history.sqlite3');result=[]
try:
    with HistoryView(path,key,salt) as view:
        for entry in scopes(Settings()):
            room=entry['configured_name']
            members=[r[0] for r in db.execute('SELECT DISTINCT sender FROM messages WHERE source=? AND room=? AND sender LIKE ? ORDER BY sender',
                                             ('wechat',room,'wxid_%'))]
            contact={}
            for offset in range(0,len(members),200):
                chunk=members[offset:offset+200]
                if chunk:
                    rows=view.query('SELECT username,nick_name FROM contact WHERE username IN ('+','.join('?' for _ in chunk)+')',tuple(chunk))
                    contact.update({username:' '.join((nick or '').split())[:128] for username,nick in rows if nick})
            group=view.query('SELECT ext_buffer FROM chat_room WHERE username=?',(entry['room_id'],))
            nicknames=group_nicknames(group[0][0]) if group else {}
            mapping={u:nicknames.get(u) or contact.get(u) or '群友'+str(i+1) for i,u in enumerate(members)}
            result.append({'room_id':entry['room_id'],'aliases':[entry['name'],room],'labels':mapping})
finally:db.close()
(ROOT/'.local/member-labels.json').write_text(json.dumps({'groups':result},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'groups':len(result),'members_mapped':[len(g['labels']) for g in result],
                  'group_nickname_priority':True,'private_contact_remarks_used':False}))
