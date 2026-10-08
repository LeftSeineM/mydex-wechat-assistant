"""Prepare an isolated, account-bound research directory for the user's M login."""
import json
from pathlib import Path
import psutil
from inspect_open_databases import inventory
from find_history_keys import scan
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'.local/quote-m-session'

def main():
    verified=json.loads((ROOT/'.local/quote-session-check.json').read_text())
    if len(verified)!=1:raise ValueError('Ambiguous client')
    session=verified[0];pid=session['pid']
    if psutil.Process(pid).create_time()!=session['created']:raise ValueError('Client restarted')
    expected=Path('D:/weixin/xwechat_files/wxid_example000002_43f1')
    if session['account_roots']!=[str(expected)]:raise ValueError('Account changed')
    files=[]
    for raw in inventory(pid)['database_paths']:
        path=Path(raw)
        if 'db_storage' not in path.parts:continue
        if expected not in path.parents:raise ValueError('Multiple active account directories')
        if path.name in ('contact.db','message_0.db','message_1.db','message_2.db','message_3.db'):
            files.append({'name':path.name,'parent':str(path.parent)})
    if not any(r['name']=='contact.db' for r in files):raise ValueError('No active contact database')
    DATA.mkdir(exist_ok=True)
    (DATA/'session.json').write_text(json.dumps({**session,'allowed_room':'90000000003@chatroom',
        'expected_nickname':'M','group':'示例工作群'},ensure_ascii=False,indent=2),encoding='utf-8')
    (DATA/'history-file-profile.json').write_text(json.dumps(files,indent=2),encoding='utf-8')
    result=scan(pid,DATA)
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
