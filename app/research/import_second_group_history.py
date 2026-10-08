"""Read and archive the explicitly requested past Let's group conversations.
Old mentions are stored as context; none invokes a model or a send.
"""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from history_reader import TargetHistory
from lab import Engine,Settings,Store
from group_scopes import GroupSettings,scopes
reader=TargetHistory(group="示例朋友群")
entry=next(g for g in scopes(Settings()) if g['room_id']==reader.room)
store=Store();engine=Engine(GroupSettings(Settings(),entry),store)
added=0;total=0;files=[];times=[]
try:
    for path in reader.message_paths():
        result=reader.fetch(path,reader.name);total+=len(result['events'])
        files.append({'file':Path(path).name,'stored_rows':result['stored_rows'],'read_rows':result['read_rows'],'rejected':result['rejected']})
        for offset in range(0,len(result['events']),1000):
            batch=result['events'][offset:offset+1000]
            added+=engine.record_history(batch)['added'];times.extend(e['created'] for e in batch)
            print(json.dumps({'phase':'importing','added':added,'file':Path(path).name}),flush=True)
    report={'group':reader.name,'added':added,'rows_read':total,'files':files,
            'first_time':min(times) if times else None,'last_time':max(times) if times else None,
            'history_completeness':'unknown','authenticated_shards':len(reader.message_paths()),
            'old_mentions_replayed':0,'automatic_messages_sent':0}
    (ROOT/'.local/second-group-history-import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report))
finally:store.db.close()
