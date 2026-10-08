"""One human-requested sign-off to each of the four enrolled groups.

The extra allowance exists only in this process for these four fixed drafts.
Normal daemon limits are unchanged; all attempts count against later budgets.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab import DATA,Settings,Store,Engine
from group_scopes import scopes,ALLOWED_ROOMS
from native_sender_bridge import NativeSender
from send_guard import POLICY

TEXT='🌙 大家晚安！我是群研究助手 Mydex，今晚先下线休息了。感谢大家今天的提问和交流，下次上线再见，祝大家好梦！'

def pause_intake():
    base='http://127.0.0.1:8769'
    with urllib.request.urlopen(base,timeout=15) as response:html=response.read().decode()
    token=re.search(r'<meta name="lab-token" content="([^"]+)"',html).group(1)
    req=urllib.request.Request(base+'/api/history/stop',b'{}',
        {'Content-Type':'application/json','X-Lab-Token':token},method='POST')
    with urllib.request.urlopen(req,timeout=15) as response:json.load(response)

def main():
    settings=Settings();groups=scopes(settings)
    if {g['room_id'] for g in groups}!=ALLOWED_ROOMS or len(groups)!=4:
        raise ValueError('The explicitly selected four groups changed')
    pause_intake()
    store=Store();engine=Engine(settings,store);sender=NativeSender(engine)
    if not sender.enabled or not sender.state(fresh=True)['connected']:
        raise ValueError('Verified sender unavailable')
    # Exactly four human-requested announcements. Never reset the circuit,
    # change pacing, erase attempts, or adjust the running daemon's policy.
    with store.lock:
        rows=store.db.execute('SELECT room,attempted FROM send_attempts WHERE attempted>?',(time.time()-86400,)).fetchall()
    now=time.time()
    POLICY['global_hour_limit']=max(POLICY['global_hour_limit'],sum(r['attempted']>now-3600 for r in rows)+4)
    POLICY['global_day_limit']=max(POLICY['global_day_limit'],len(rows)+4)
    POLICY['group_hour_limit']=max(POLICY['group_hour_limit'],max(sum(r['room']==g['configured_name'] and r['attempted']>now-3600 for r in rows) for g in groups)+1)
    POLICY['group_day_limit']=max(POLICY['group_day_limit'],max(sum(r['room']==g['configured_name'] for r in rows) for g in groups)+1)
    results=[]
    for group in groups:
        room=group['configured_name']
        key='approved-goodnight-20261008-'+hashlib.sha256(group['room_id'].encode()).hexdigest()[:16]
        with store.lock,store.db:
            previous=store.db.execute('SELECT state FROM outbox WHERE id=?',(key,)).fetchone()
            if previous:
                results.append({'group':group['name'],'state':previous['state'],'repeated':False})
                continue
            stamp=time.time()
            store.db.execute('INSERT INTO messages(source,room,sender,content,role,event_id,created,message_time) VALUES(?,?,?,?,?,?,?,?)',
                ('wechat',room,'Mydex',TEXT,'assistant',key,stamp,stamp))
            store.db.execute('INSERT INTO outbox(id,room,content,state,created,source,event_id) VALUES(?,?,?,?,?,?,?)',
                (key,room,TEXT,'draft',stamp,'wechat',key))
        try:
            outcome=sender.send_draft(key)
            record={'group':group['name'],'draft_id':key,**outcome}
        except Exception as exc:
            record={'group':group['name'],'draft_id':key,'status':'not_confirmed','error':type(exc).__name__}
        results.append(record)
        (DATA/'goodnight-20261008-deliveries.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(record,ensure_ascii=False),flush=True)
        if sender.guard.state()['blocked']:break
    store.db.close()

if __name__=='__main__':main()
