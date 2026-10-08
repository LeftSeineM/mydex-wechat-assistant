"""Send one human-authorized startup per newly selected group via guarded API."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'.local';BASE='http://127.0.0.1:8769'

def get(path):
    with urllib.request.urlopen(BASE+path,timeout=8) as response:return json.load(response)

def main():
    selected=json.loads((DATA/'new-group-selections.json').read_text(encoding='utf-8'))
    if {e['room_id'] for e in selected}!={'90000000001@chatroom','90000000005@chatroom'}:raise ValueError('Unexpected selection')
    state=get('/api/state')
    if not state['native_sender']['connected'] or not state['native_sender']['enabled']:raise ValueError('Sender not ready')
    running={g.get('group_name') for g in state['group_states'] if g.get('running') and g.get('phase')=='watching'}
    if not {e['name'] for e in selected}<=running:raise ValueError('New group listeners not ready')
    results=[]
    for entry in selected:
        text=('👋 我是群研究助手Mydex，已上线！\n\n'
              f"用微信成员选择功能 @{entry['mention_name']} ＋ 问题，我就会在本群回答。\n\n"
              '可以找我：知识问答、资料查询、写作翻译，以及整理接入后的讨论和待办。\n'
              '例如：“帮我解释一下这个概念”“总结接入后的群聊”。\n\n'
              '我只在被 @ 时回复；回答会使用本群接入后的相关文字，由OpenAI在线模型生成。')
        key='approved-startup-'+hashlib.sha256((entry['room_id']+text).encode()).hexdigest()[:24]
        db=sqlite3.connect(DATA/'history.sqlite3',timeout=15)
        try:
            with db:
                db.execute('BEGIN IMMEDIATE')
                previous=db.execute('SELECT state FROM outbox WHERE id=?',(key,)).fetchone()
                if previous:
                    results.append({'group':entry['name'],'status':'already_prepared','state':previous[0]});continue
                now=time.time()
                db.execute('INSERT INTO messages(source,room,sender,content,role,event_id,created,message_time) VALUES(?,?,?,?,?,?,?,?)',
                           ('wechat',entry['name'],'Mydex',text,'assistant',key,now,now))
                db.execute('INSERT INTO outbox(id,room,content,state,created,source,event_id) VALUES(?,?,?,?,?,?,?)',
                           (key,entry['name'],text,'draft',now,'wechat',key))
        finally:db.close()
        with urllib.request.urlopen(BASE,timeout=8) as response:html=response.read().decode('utf-8')
        token=re.search(r'<meta name="lab-token" content="([^"]+)"',html).group(1)
        request=urllib.request.Request(BASE+'/api/native/send',json.dumps({'id':key}).encode(),
                                      {'Content-Type':'application/json','X-Lab-Token':token},method='POST')
        with urllib.request.urlopen(request,timeout=8) as response:job=json.load(response)['job_id']
        record={'group':entry['name'],'mention_name':entry['mention_name'],'draft_id':key,'job_id':job}
        end=time.monotonic()+55
        while time.monotonic()<end:
            response=get('/api/job?id='+job)
            if response['status'] in ('done','error'):
                record.update(response);break
            time.sleep(.5)
        results.append(record)
        (DATA/'new-group-startup-deliveries.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(record,ensure_ascii=False),flush=True)
        if record.get('result',{}).get('status')!='sent':break

if __name__=='__main__':main()
