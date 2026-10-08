"""Publish the ranking explicitly approved by the human, once, via send limits."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'.local'
BASE='http://127.0.0.1:8769'
GROUP="示例朋友群"

def get(path):
    with urllib.request.urlopen(BASE+path,timeout=8) as response:return json.load(response)

def main():
    proof=json.loads((DATA/'history-model-proof.json').read_text(encoding='utf-8'))
    if proof['group']!=GROUP:raise ValueError('Wrong proof group')
    scope=proof['record_scope'];stats=scope['statistics']
    if stats['metric']!='laugh_messages' or stats['matched_messages']!=192:
        raise ValueError('Ranking changed; this approval is for the displayed result')
    lines=[f"{i}. {r['member']}：{r['count']}条" for i,r in enumerate(stats['ranking'],1)]
    content=('😂 本群“哈哈”排行榜来啦！\n\n'+'\n'.join(lines)+
             '\n\n共192条。按连续两个及以上“哈”的消息统计，长度不限，每条消息算一次。'
             '\n范围：2026年7月27日至10月7日23:08，本机已取得的群历史；不包含图片、表情包里的笑声，尚不能保证历史全部齐全。')
    # A stable ID prevents rerunning this helper from creating another notice.
    key='approved-laugh-ranking-'+hashlib.sha256(content.encode()).hexdigest()[:24]
    state=get('/api/state')
    if not state['native_sender'].get('connected') or not state['native_sender'].get('enabled'):
        raise ValueError('Verified sender is not connected')
    db=sqlite3.connect(DATA/'history.sqlite3',timeout=15)
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT state,content FROM outbox WHERE id=?',(key,)).fetchone()
            if prior:
                print(json.dumps({'status':'already_prepared','state':prior[0],'resubmitted':False}));return
            now=time.time()
            db.execute('INSERT INTO messages(source,room,sender,content,role,event_id,created,message_time) VALUES(?,?,?,?,?,?,?,?)',
                       ('wechat',GROUP,'Mydex',content,'assistant',key,now,now))
            db.execute('INSERT INTO outbox(id,room,content,state,created,source,event_id) VALUES(?,?,?,?,?,?,?)',
                       (key,GROUP,content,'draft',now,'wechat',key))
    finally:db.close()
    with urllib.request.urlopen(BASE,timeout=8) as response:html=response.read().decode('utf-8')
    token=re.search(r'<meta name="lab-token" content="([^"]+)"',html).group(1)
    request=urllib.request.Request(BASE+'/api/native/send',json.dumps({'id':key}).encode(),
                                   {'Content-Type':'application/json','X-Lab-Token':token},method='POST')
    with urllib.request.urlopen(request,timeout=8) as response:job_id=json.load(response)['job_id']
    report={'group':GROUP,'draft_id':key,'job_id':job_id,'status':'pending'}
    path=DATA/'laugh-ranking-delivery.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    deadline=time.monotonic()+55
    while time.monotonic()<deadline:
        job=get('/api/job?id='+job_id)
        if job['status'] in ('done','error'):
            report.update(job)
            path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report,ensure_ascii=False));return
        time.sleep(.6)
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
