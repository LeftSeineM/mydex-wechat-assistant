"""Resolve only the newly user-selected Let's dog group from local contacts."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from history_reader import TargetHistory
from research.history_vfs import HistoryView
reader=TargetHistory()
contacts=[p for p in reader.keys if Path(p).name=='contact.db']
if len(contacts)!=1:raise ValueError('Authenticated contacts unavailable')
key,salt=reader.keys[contacts[0]]
with HistoryView(contacts[0],key,salt) as view:
    rows=view.query('SELECT username,nick_name FROM contact WHERE username LIKE ? AND nick_name LIKE ? LIMIT 10',
                    ('%@chatroom',"Let's%"))
matches=[{'room_id':row[0],'name':row[1]} for row in rows]
(ROOT/'.local/requested-group-candidates.json').write_text(json.dumps(matches,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(matches,ensure_ascii=False))
