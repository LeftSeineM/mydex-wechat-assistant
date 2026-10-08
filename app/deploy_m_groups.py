"""User-authorized rollout to the two verified groups, with receipt checks."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
import psutil
from lab import ROOT,Settings,Store,Engine
from session_history import SessionHistory
from group_scopes import GroupSettings
from m_session_assistant import DATA,check_session,matches,save
from research.worker_sender_v4.run import action as v4
from research.worker_sender_v5.run import action as v5

def main():
    session=json.loads((DATA/'session.json').read_text(encoding='utf-8'));check_session(session)
    names=['示例工作群','示例讨论群','示例学习群']
    readers=[SessionHistory(DATA,group=name) for name in names]
    settings=Settings()
    settings.update({'conversation_enabled':True})
    entries=[{'configured_name':name,'name':r.name,'room_id':r.room,
              'group_model_authorized':True,'history_import':True,'added_at':time.time()} for name,r in zip(names,readers)]
    store=Store(DATA/'history.sqlite3')
    for entry,reader in zip(entries,readers):
        engine=Engine(GroupSettings(settings,entry),store,data=DATA)
        cursors={}
        for path in reader.message_paths():
            result=reader.fetch(path,entry['configured_name'])
            for i in range(0,len(result['events']),2000):engine.record_history(result['events'][i:i+2000])
            cursors[path]=result['cursor']
        suffix=hashlib.md5(reader.room.encode()).hexdigest()
        save('database-inbox-'+suffix+'-cursor.json',{'room':entry['configured_name'],'cursors':cursors})
    save('monitored-groups.json',entries)
    old_status=json.loads((DATA/'assistant-status.json').read_text(encoding='utf-8'))
    old=psutil.Process(old_status['runner_pid'])
    if str(ROOT/'m_session_assistant.py').lower() not in [str(a).lower() for a in old.cmdline()]:raise ValueError('Unexpected runner')
    native=v4(session['pid'],'status',data=DATA)
    if native['phase']!=2 or not native['worker_thread'] or native['pending']:raise ValueError('Existing sender not idle')
    (DATA/'stop.request').write_text('rolling multi-group update',encoding='utf-8')
    old.wait(timeout=15)
    stopped=v4(session['pid'],'stop',data=DATA)
    if stopped['phase']!=5:raise ValueError('Old native sender did not stop')
    installed=v5(session['pid'],'install',data=DATA)
    if installed['return_code']!=0 or installed['phase']!=2:raise ValueError('New sender not installed')
    ready=v5(session['pid'],'status',data=DATA)
    if not ready['worker_thread']:
        ready=v5(session['pid'],'adopt',adopt_thread=native['worker_thread'],data=DATA)
    if not ready['worker_thread'] or ready.get('return_code') not in (None,0):raise ValueError('Worker binding not ready')
    config=json.loads((DATA/'native-sender-settings.json').read_text(encoding='utf-8'))
    save('native-sender-settings.json',{**config,'sender_version':5,'sender_sha256':ready['sender_sha256']})
    deliveries=[]
    for reader in readers[1:]:
        body=('Mydex：\n我是群研究助手Mydex，已在「'+reader.name+'」上线。\n\n'
              '由千问 Qwen3.8-Flash 提供回答。可以 @M 提问；不 @ 时也会回应明确问题，少量参与闲聊。\n'
              '支持常识问答、写作与编程、群聊总结、待办整理。连续相关发言会合并，忙时排队，各群内容分开处理。\n'
              '历史以本机已同步内容为准；当前没有联网搜索。')
        filename='online-'+reader.room.split('@')[0]+'.json'
        if (DATA/filename).exists():raise ValueError('Announcement already attempted; inspect receipt before retry')
        check_session(session)
        cursor={p:reader.latest_cursor(p,reader.name) for p in reader.message_paths()}
        start=time.time();save(filename,{'state':'intent','at':start,'body':body,'room_id':reader.room,'cursors':cursor})
        queued=v5(session['pid'],'send',body,room=reader.room,data=DATA)
        if queued['return_code']!=0:raise ValueError('Announcement rejected; not retrying')
        deadline=time.monotonic()+35;event=None
        while time.monotonic()<deadline:
            check_session(session);event=matches(reader,body,start,cursor)
            if event:break
            time.sleep(.4)
        if not event:raise ValueError('Receipt unknown; not retrying')
        delivery={'group':reader.name,'room_id':reader.room,'state':'sent','server_record_verified':True,'server_id':event['id'],'at':time.time()}
        save(filename,delivery);deliveries.append(delivery);print(json.dumps(delivery,ensure_ascii=False),flush=True)
    save('new-groups-delivery.json',deliveries)
    (DATA/'stop.request').unlink()
    with (DATA/'assistant.stdout.log').open('ab') as out,(DATA/'assistant.stderr.log').open('ab') as err:
        proc=subprocess.Popen([sys.executable,'-u',str(ROOT/'m_session_assistant.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
             creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB,close_fds=True)
    print(json.dumps({'launched':proc.pid,'groups':names,'model':'Qwen3.8-Flash','model_parallel_cap':4}),flush=True)

if __name__=='__main__':main()
