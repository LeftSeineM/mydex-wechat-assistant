"""One user-requested interaction grounded in the authorized group's old chat."""
import json
from pathlib import Path
import sqlite3
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab import Backend,Settings
from member_labels import display_sender,prettify_reply
room="示例朋友群"
groups=json.loads((ROOT/'.local/monitored-groups.json').read_text(encoding='utf-8'))
cutoff=next(g['added_at'] for g in groups if g['configured_name']==room)
db=sqlite3.connect(ROOT/'.local/history.sqlite3');db.row_factory=sqlite3.Row
rows=db.execute('SELECT * FROM messages WHERE source=? AND room=? AND role=? AND message_time<? AND content NOT LIKE ? ORDER BY message_time DESC LIMIT 180',
                ('wechat',room,'user',cutoff,'【%')).fetchall();db.close()
records=[{'id':r['event_id'],'sender':display_sender(r['sender'],room),'text':r['content'],'time':r['message_time']}
          for r in reversed(rows) if not r['content'].startswith(('Mydex：','小研：','M：'))]
cfg=Settings().get();cfg.update(group_data=True,web_search_enabled=False)
question='根据以下本群较早的真实聊天，挑一个适合继续讨论的公开话题，写一段自然的群聊互动，最多100字。先提大家之前具体聊过什么，再问一个具体问题；不要提私人或尴尬话题，不要点名，不能捏造记录中没有的内容。不要重复助手上线、自我介绍、扫码测试等话题。只输出这段可发给群友的话。'
reply=Backend().reply(cfg,[{'role':'user','content':json.dumps(records,ensure_ascii=False)},
                         {'role':'user','content':question}])
reply=prettify_reply(reply.strip(),room)
report={'group':room,'reply':reply,'input_records':len(records),
        'old_records_before':cutoff,'source_ids':[r['id'] for r in records],
        'grounded_in_target_group_history':True,'sent':False}
(ROOT/'.local/history-interaction-draft.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'group':room,'reply':reply,'input_records':len(records)},ensure_ascii=False))
