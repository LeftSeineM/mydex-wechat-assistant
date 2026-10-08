"""Refresh only the two authorized groups after active-account verification.
Old messages never trigger a model or a send. Print counts, not chat bodies.
"""
import json
from pathlib import Path
import sys
import psutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'))
from inspect_open_databases import inventory
from history_reader import TargetHistory
from lab import Store, Settings, Engine
from group_scopes import scopes,GroupSettings
from history_context import retrieve

def main():
    settings=Settings();groups=scopes(settings)
    readers=[TargetHistory(group=g['configured_name']) for g in groups]
    processes=[]
    for proc in psutil.process_iter(['name','exe','cmdline']):
        if (proc.info['name'] or '').lower()!='weixin.exe':continue
        if any('--type=' in a or 'crash' in a.lower() for a in (proc.info['cmdline'] or [])):continue
        if Path(proc.info['exe']).resolve()==Path('C:/Program Files/Tencent/Weixin/Weixin.exe').resolve():processes.append(proc)
    if len(processes)!=1:raise ValueError('Expected one logged-in client')
    roots=set()
    for raw in inventory(processes[0].pid)['database_paths']:
        for p in Path(raw).parents:
            if p.name=='db_storage':roots.add(p.parent)
    if len(roots)!=1 or any(r.account_root not in roots for r in readers):
        raise ValueError('Active account differs; no history imported')
    report={'groups':[],'old_mentions_replayed':0,'messages_sent':0}
    store=Store()
    try:
        for group,reader in zip(groups,readers):
            engine=Engine(GroupSettings(settings,group),store)
            added=0;read=0
            for path in reader.message_paths():
                result=reader.fetch(path,group['configured_name'])
                if result['rejected']:raise ValueError('History decoding rejected rows')
                read+=len(result['events'])
                for offset in range(0,len(result['events']),1000):
                    added+=engine.record_history(result['events'][offset:offset+1000])['added']
            row={'group':group['name'],'read_rows':read,'newly_archived':added,'history_completeness':'unknown'}
            for name,question in [('laugh','谁最爱发连续的哈哈'),('yesterday','总结昨天群聊')]:
                _,details=retrieve(store,'wechat',group['configured_name'],question,'local-read-only-check',limit=5)
                row[name]=details
            report['groups'].append(row)
    finally:store.db.close()
    (ROOT/'.local/history-retrieval-proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
