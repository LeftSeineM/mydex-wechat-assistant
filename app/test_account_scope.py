import json,tempfile,time,unittest
from pathlib import Path
from lab import Settings,Store,Engine
from account_scope import peer_kind,validate_recipient
from account_assistant import AccountInbox

class FakeReader:
    def message_paths(self):return ['message_0.db']

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.store=Store(self.root/'history.db');self.settings=Settings(self.root/'settings.json')
        self.engine=Engine(self.settings,self.store)
        self.entry={'peer':'wxid_test','kind':'direct','registered_since':time.time()-1,'previously_enabled':False}
        self.inbox=AccountInbox(self.engine,self.root,entry=self.entry,reader_factory=FakeReader)
    def tearDown(self):self.store.db.close();self.tmp.cleanup()
    def event(self,**changes):
        return {'id':'1','source':'wechat','room':'AI助手测试群','sender':'wxid_test','content':'你好',
                'type':'text','created':time.time(),'is_self':False,**changes}
    def jobs(self):return self.store.db.execute('SELECT * FROM model_jobs').fetchall()
    def test_private_text_queues_without_mention(self):
        self.inbox.consider_event(self.event())
        self.assertTrue(json.loads(self.jobs()[0]['event'])['direct_verified'])
    def test_old_messages_self_and_wrong_peer_never_reply(self):
        for changes in ({'created':time.time()-20},{'is_self':True},{'sender':'somebody_else'},{'type':'system'}):
            self.inbox.consider_event(self.event(**changes))
        self.assertEqual(self.jobs(),[])
    def test_new_groups_still_require_true_at(self):
        self.entry['kind']='group'
        self.inbox.consider_event(self.event())
        self.assertEqual(self.jobs(),[])
        self.inbox.consider_event(self.event(mention_verified=True))
        self.assertEqual(len(self.jobs()),1)
    def test_private_attachments_get_honest_placeholder_context(self):
        self.inbox.consider_event(self.event(type='attachment',content='【群文件】方案.pdf，文件正文尚未读取。'))
        self.assertEqual(len(self.jobs()),1)
    def test_system_subscriptions_and_invalid_targets_excluded(self):
        for peer in ('filehelper','weixin','gh_example','abc@evil','bad/peer',''):
            self.assertIsNone(peer_kind(peer))
        self.assertEqual(peer_kind('12345678@chatroom'),'group')
        self.assertEqual(peer_kind('legacy.friend'),'direct')

if __name__=='__main__':unittest.main()
