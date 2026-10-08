"""Enable the user's explicit all-group-mentions plus personal-DM request."""
import json,subprocess,sys,time
from pathlib import Path
import psutil
from lab import ROOT,Settings
from m_session_assistant import DATA,save,check_session
from account_scope import discover
from session_history import SessionHistory
from research.worker_sender_v5.run import action as old_action
from research.worker_sender_v6.run import action as new_action

def main():
    session=json.loads((DATA/'session.json').read_text(encoding='utf-8'));check_session(session)
    path=DATA/'reply-scope.json'
    if not path.exists():
        save('reply-scope.json',{'pid':session['pid'],'process_created':session['created'],
             'account_root':session['account_roots'][0],'activated_at':time.time(),
             'all_groups_mentions':True,'all_direct_messages':True,'source':'explicit_user_request'})
    base=SessionHistory(DATA);registry=discover(base,DATA)
    print(json.dumps({'authenticated_conversations':len(registry),'scope':'all_group_mentions_and_direct_messages'}),flush=True)
    deadline=time.monotonic()+45
    while True:
        current=json.loads((DATA/'assistant-status.json').read_text(encoding='utf-8'))
        native=old_action(session['pid'],'status',data=DATA)
        if not any(g.get('model_busy') for g in current.get('groups',[])) and not native['pending']:break
        if time.monotonic()>deadline:raise RuntimeError('Existing replies still active; no interruption performed')
        time.sleep(1)
    proc=psutil.Process(current['runner_pid'])
    if str(ROOT/'m_session_assistant.py').lower() not in [str(a).lower() for a in proc.cmdline()]:raise ValueError('Unexpected runner')
    (DATA/'stop.request').write_text('enable all requested conversations',encoding='utf-8')
    proc.wait(timeout=30)
    stopped=old_action(session['pid'],'stop',data=DATA)
    if stopped['phase']!=5:raise ValueError('Old sender not stopped')
    installed=new_action(session['pid'],'install',data=DATA)
    if installed['return_code'] or installed['phase']!=2:raise ValueError('New sender installation failed')
    ready=new_action(session['pid'],'status',data=DATA)
    if not ready['worker_thread']:
        ready=new_action(session['pid'],'adopt',adopt_thread=native['worker_thread'],data=DATA)
    if not ready['worker_thread'] or ready.get('return_code') not in (0,None):raise ValueError('Worker binding failed')
    cfg=json.loads((DATA/'native-sender-settings.json').read_text(encoding='utf-8'))
    save('native-sender-settings.json',{**cfg,'sender_version':6,'sender_sha256':ready['sender_sha256']})
    Settings().update({'conversation_enabled':False})
    (DATA/'stop.request').unlink()
    with (DATA/'account-assistant.stdout.log').open('ab') as out,(DATA/'account-assistant.stderr.log').open('ab') as err:
        child=subprocess.Popen([sys.executable,'-u',str(ROOT/'account_assistant.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
             creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB,close_fds=True)
    print(json.dumps({'launched':child.pid,'sender_version':6,'proactive_messages_sent':0}),flush=True)

if __name__=='__main__':main()
