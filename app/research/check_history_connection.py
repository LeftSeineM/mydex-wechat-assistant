"""Inspect the selected groups and active account using read-only metadata.
Never extracts keys, sends messages, or installs a native hook.
"""
import json
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
import urllib.request
import psutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'))
from inspect_open_databases import inventory
from history_reader import TargetHistory

def stamp(value):
    return datetime.fromtimestamp(value,timezone(timedelta(hours=8))).isoformat() if value else None

def main():
    data=ROOT/'.local'
    groups=json.loads((data/'monitored-groups.json').read_text(encoding='utf-8'))
    previous=json.loads((data/'group-binding.json').read_text(encoding='utf-8'))
    report={'processes':[],'cached_groups':[],'live_history':[], 'messages_sent':0}
    active_roots=set()
    for proc in psutil.process_iter(['name','exe','cmdline']):
        if (proc.info['name'] or '').lower()!='weixin.exe':continue
        args=proc.info['cmdline'] or []
        if any('--type=' in a or 'crash' in a.lower() for a in args):continue
        if Path(proc.info['exe']).resolve()!=Path('C:/Program Files/Tencent/Weixin/Weixin.exe').resolve():continue
        row={'pid':proc.pid,'process_created':proc.create_time()}
        try:
            paths=inventory(proc.pid)['database_paths']
            for raw in paths:
                p=Path(raw)
                for parent in p.parents:
                    if parent.name=='db_storage':active_roots.add(parent.parent)
            row['opened_database_count']=len(paths)
        except Exception as exc:row['error']=type(exc).__name__
        report['processes'].append(row)
    report['active_account_directories']=[p.name for p in active_roots]
    report['same_as_previous_account']=len(active_roots)==1 and next(iter(active_roots)).name.startswith(previous['account_id']+'_')
    db=sqlite3.connect((data/'history.sqlite3').as_uri()+'?mode=ro',uri=True)
    try:
        for group in groups:
            values=(group['configured_name'],)
            rows=db.execute("SELECT role,COUNT(*),MIN(COALESCE(message_time,created)),MAX(COALESCE(message_time,created)) FROM messages WHERE source='wechat' AND room=? GROUP BY role",values).fetchall()
            report['cached_groups'].append({'group':group['name'],'records':[{'role':r[0],'count':r[1],'first':stamp(r[2]),'last':stamp(r[3])} for r in rows]})
    finally:db.close()
    if report['same_as_previous_account']:
        for group in groups:
            try:
                reader=TargetHistory(group=group['configured_name'])
                if reader.account_root not in active_roots:raise ValueError('Account root mismatch')
                files=[]
                for path in reader.message_paths():
                    result=reader.fetch(path,group['configured_name'])
                    times=[e['created'] for e in result['events']]
                    files.append({'file':Path(path).name,'stored_rows':result['stored_rows'],
                                  'read_rows':result['read_rows'],'rejected':result['rejected'],
                                  'first':stamp(min(times)) if times else None,
                                  'last':stamp(max(times)) if times else None})
                report['live_history'].append({'group':group['name'],'files':files,'history_completeness':'unknown'})
            except Exception as exc:report['live_history'].append({'group':group['name'],'error':type(exc).__name__})
    try:
        state=json.load(urllib.request.urlopen('http://127.0.0.1:8769/api/state',timeout=8))
        report['service']={'native':state['native_sender'],'waiting_for_binding':state.get('monitoring_waiting_for_binding'),
                           'groups':[{'group':g.get('group_name'),'running':g['running'],'phase':g.get('phase'),'error':g.get('last_error')} for g in state['group_states']]}
    except Exception as exc:report['service']={'error':type(exc).__name__}
    (data/'history-connection-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
