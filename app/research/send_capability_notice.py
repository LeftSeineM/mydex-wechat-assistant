"""Publish only the capabilities that are already enabled and verified."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from history_reader import TargetHistory
from research.worker_sender_v3.run import action
TEXT='''Mydex：
👋 大家好，我是群研究助手Mydex，已上线！

现在可以找我：
• 解答知识问题：历史地理、编程、语言学习、写作和思路分析。
• 回顾群聊：总结讨论、查之前聊过的话题、整理观点与待办。
• 继续聊旧话题：根据本群的历史讨论接话、比较想法、提一些新问题。
• 整理信息：把零散发言变成清单、摘要或行动建议。

用微信成员选择功能 @示例账号 ＋ 问题就行，例如“我们之前聊过哪些学习方法？”
常识题不用先在群里讲过；关于群友的个人情况，我会以真实记录为准，不乱猜。'''
reader=TargetHistory(group="示例朋友群")
cursors={p:reader.fetch(p,reader.name)['cursor'] for p in reader.message_paths()}
queued=action(55832,'send',TEXT,room=reader.room)
if queued['return_code']:raise ValueError('Notice not accepted')
matches=[];end=time.monotonic()+20
while time.monotonic()<end:
    for path,cursor in cursors.items():
        events=reader.fetch(path,reader.name,cursor)['events']
        matches=[e['id'] for e in events if e['content']==TEXT and e.get('is_self') and e['id'].isdigit() and int(e['id'])]
        if matches:break
    if matches:break
    time.sleep(.4)
proof={'group':reader.name,'server_record_verified':bool(matches),'reply_ids':matches,
       'capabilities':['general_knowledge','group_history','history_interaction','summaries_and_lists']}
(ROOT/'.local/capability-notice-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(proof,ensure_ascii=False))
