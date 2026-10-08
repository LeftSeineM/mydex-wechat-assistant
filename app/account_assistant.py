"""New group @s and personal DMs for the user's current authorized account."""
import hashlib,json,msvcrt,threading,time
from pathlib import Path
import psutil
from lab import Settings,Store,Engine,Backend,UserError
from group_scopes import GroupSettings
from m_session_assistant import DATA,save,check_session
from session_history import SessionHistory
from account_scope import discover,load_scope,AccountHistory,validate_recipient
from conversation_queue import ConversationInbox,LimitedBackend
from native_sender_bridge import NativeSender

class AccountInbox(ConversationInbox):
    def __init__(self,*args,entry,**kwargs):
        self.entry=entry
        super().__init__(*args,**kwargs)
        if not self.checkpoint.exists():
            reader=self.reader_factory()
            self.cursors={p:0 for p in reader.message_paths()}
    def consider_event(self,event):
        if not self.entry.get('previously_enabled') and event.get('created',0)<self.entry['registered_since']:return
        if self.entry['kind']=='direct':
            if (not event.get('is_self') and event.get('sender')==self.entry['peer']
                    and event.get('type')!='system'):
                self.enqueue({**event,'direct_verified':True})
            return
        super().consider_event(event)

class AccountSender(NativeSender):
    def __init__(self,engine,session,base,registry):
        self.session=session;self.base=base;self.registry=registry
        super().__init__(engine,data=DATA)
    def verify_session(self):
        super().verify_session();check_session(self.session)
    def allowed_targets(self):
        return {entry['configured_name']:peer for peer,entry in self.registry.copy().items()}
    def reader(self,group=None):
        entry=next((v for v in self.registry.copy().values() if v['configured_name']==group),None)
        if entry is None:raise UserError('会话未登记')
        validate_recipient(DATA,entry['peer'])
        return AccountHistory(self.base,entry)

def main():
    lock=open(DATA/'assistant.lock','a+b');lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
    try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:return
    inboxes={};sender=None;model_threads=[]
    def report(phase,**extra):
        save('assistant-status.json',{'phase':phase,'runner_pid':psutil.Process().pid,'at':time.time(),
             'runtime':'account_assistant','mode':'all_group_mentions_and_private_messages',**extra})
    try:
        session=json.loads((DATA/'session.json').read_text(encoding='utf-8'));check_session(session)
        scope=load_scope(DATA);base=SessionHistory(DATA);settings=Settings()
        store=Store(DATA/'history.sqlite3');backend=LimitedBackend(Backend())
        registry=discover(base,DATA);main_engine=Engine(settings,store,backend=backend,data=DATA)
        sender=AccountSender(main_engine,session,base,registry)
        if not sender.state(fresh=True)['connected']:raise UserError('发送组件未连接')
        checked=0
        while not (DATA/'stop.request').exists():
            check_session(session)
            if time.monotonic()-checked>=3:
                base.refresh_keys()
                refreshed=discover(base,DATA);registry.update(refreshed);checked=time.monotonic()
                for peer,entry in list(registry.items()):
                    if peer in inboxes or (not entry['previously_enabled'] and entry['last_message_time']<scope['activated_at']):continue
                    reader=AccountHistory(base,entry)
                    engine=Engine(GroupSettings(settings,entry),store,backend=backend,data=DATA)
                    inbox=AccountInbox(engine,data=DATA,reader_factory=lambda r=reader:r,sender=sender,scope=peer,entry=entry)
                    inbox.start();inboxes[peer]=inbox
            report('running',account='M',model=settings.get()['model'],model_concurrency_limit=4,
                   queue_capacity_per_conversation=100,all_groups_mentions=True,all_direct_messages=True,
                   discovered_conversations=len(registry),sender=sender.state(),
                   groups=[{'name':i.entry['name'],'kind':i.entry['kind'],**i.state()} for i in inboxes.values()])
            time.sleep(1)
        report('stopping')
    except Exception as exc:
        report('needs_attention',error=str(exc) if isinstance(exc,UserError) else type(exc).__name__)
    finally:
        if sender:sender.enabled=False
        for item in inboxes.values():item.stop()
        for item in inboxes.values():
            if item.thread:item.thread.join(timeout=3)
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()

if __name__=='__main__':main()
