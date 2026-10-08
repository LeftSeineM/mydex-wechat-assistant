"""Ask the authorized model against an isolated in-memory archive copy.
No native sender, production outbox write, or real group message is involved.
"""
import json
from pathlib import Path
import sqlite3
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab import Store,Settings,Engine
from group_scopes import GroupSettings,scopes

def main():
    cfg=Settings();entry=next(g for g in scopes(cfg) if g['room_id']=='90000000006@chatroom')
    store=Store(':memory:')
    source=sqlite3.connect((ROOT/'.local/history.sqlite3').as_uri()+'?mode=ro',uri=True)
    try:source.backup(store.db)
    finally:source.close()
    class ProbeSettings:
        def get(self):
            return {**GroupSettings(cfg,entry).get(),'summary_messages':12,'summary_max_chars':8000}
    started=time.monotonic()
    try:
        result=Engine(ProbeSettings(),store).process({'source':'wechat','room':entry['configured_name'],
            'sender':'本机历史验证','content':'谁最爱发连续的哈哈？请按已归档历史统计，列前三名和匹配总条数，说明覆盖范围。',
            'id':'local-history-verification-'+str(time.time_ns()),'created':time.time(),
            'mention_verified':True,'is_self':False,'type':'text'})
        proof={'group':entry['name'],'reply':result['reply'],'record_scope':result['record_scope'],
               'elapsed_seconds':round(time.monotonic()-started,2),'sent_to_group':False,'production_draft_created':False}
        (ROOT/'.local/history-model-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(proof,ensure_ascii=False))
    finally:store.db.close()

if __name__=='__main__':main()
