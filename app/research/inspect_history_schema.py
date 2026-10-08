"""Read authenticated DB schemas and only the configured target-group contact.
No plaintext whole-database export; no unrelated contact/message rows returned.
"""
import hashlib,json
from pathlib import Path
import time
from history_crypto import dpapi
from history_vfs import HistoryView,SnapshotChanged
from run_native_observer import ROOT
def inspect():
    evidence=json.loads((ROOT/'.local/outbound-sample-evidence.json').read_text(encoding='utf-8-sig'))
    room=evidence['room_id_candidate'];target='Msg_'+hashlib.md5(room.encode()).hexdigest()
    private=json.loads(dpapi((ROOT/'.local/history-keys.dpapi').read_bytes(),True))
    allowed={str(Path(row['parent'])/row['name']) for row in json.loads((ROOT/'.local/history-file-profile.json').read_text())}
    report={'target_table':target,'group_name_expected':evidence['group_name'],'group_name_verified':False,'files':[]}
    for item in private['files']:
        if item['path'] not in allowed:continue
        path=Path(item['path'])
        for attempt in range(3):
            try:
                with HistoryView(path,bytes.fromhex(item['key']),bytes.fromhex(item['salt'])) as view:
                    tables=view.query("SELECT name,sql FROM sqlite_master WHERE type='table'")
                    matches=[(name,sql) for name,sql in tables if name.lower()==target.lower()]
                    bases=[(name,sql) for name,sql in tables if not name.lower().startswith(('msg_','chat_'))]
                    info={'name':path.name,'table_count':len(tables),'target_tables':matches,
                          'base_tables':bases,'pages_read':view.snapshot.pages_read,'wal_applied_pages':len(view.snapshot.overlay)}
                    if path.name=='contact.db':
                        for name,sql in bases:
                            if name.lower()!='contact':continue
                            columns=[r[1] for r in view.query('PRAGMA table_info("contact")')]
                            info['contact_columns']=columns
                            if 'username' in columns:
                                selected=[c for c in ('username','nick_name','nickname','remark') if c in columns]
                                rows=view.query('SELECT '+','.join('"'+c+'"' for c in selected)+' FROM "contact" WHERE username=?',(room,))
                                info['target_contact']=[dict(zip(selected,r)) for r in rows]
                                report['group_name_verified']=any(evidence['group_name'] in r.values() for r in info['target_contact'])
                    report['files'].append(info);break
            except SnapshotChanged:
                if attempt==2:report['files'].append({'name':path.name,'error':'snapshot_changed'})
                time.sleep(.1)
    (ROOT/'.local/history-schema.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
if __name__=='__main__':print(json.dumps(inspect(),ensure_ascii=False))
