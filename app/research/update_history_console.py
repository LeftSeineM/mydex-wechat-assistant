"""One-time update of the local console after authenticated history support."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
path=root/'index.html'
html=path.read_text(encoding='utf-8')
changes={
    "let current='simulation'": "let current=new URLSearchParams(location.search).get('mode')==='protocol'?'wechat':'simulation'",
    "new Date(r.created*1000).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})": "new Date((r.message_time||r.created)*1000).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})",
    '正在读取本机记录范围…</p><h3>连接真实微信群</h3>': '正在读取本机记录范围…</p><div class="buttons"><button class="primary" id="history-summary">生成群聊总结</button><button id="history-stop">停止历史监听</button></div><h3>连接真实微信群</h3>',
    "$('group-label').firstChild.textContent=d.settings.group;$('chat-title').textContent=d.settings.group;": "const groupName=d.database_inbox.group_name||d.settings.group;$('group-label').firstChild.textContent=groupName;$('chat-title').textContent=groupName;$('group-label').querySelector('small').textContent=d.database_inbox.running?'已核对本机群标识 · 正在持续监听':'目标群本机研究';",
    "drawMessages(d[current]);": "for(const t of ['simulation','wechat'])$('tab-'+t).classList.toggle('active',t===current);$('composer').classList.toggle('hidden',current==='wechat');$('channel-note').textContent=current==='wechat'?'目标群真实记录 · @ 回复目前生成本机草稿':'本地模拟 · 测试消息不会发到微信';drawMessages(d[current]);",
    "const c=state.record_scope;$('history-status').textContent='本机已记录 '+c.stored_messages+' 条，单次总结最多使用 '+state.settings.summary_messages+' 条。历史完整性待核实；附件正文尚未接入。';": "const c=state.record_scope,h=state.database_inbox;$('history-status').textContent=(h.running?'数据库持续监听中':'数据库监听已停')+' · 本机已记录 '+c.stored_messages+' 条 · 新消息 '+(h.new_messages||0)+' 条 · 总结草稿 '+(h.drafts||0)+' 条。已取得 '+(h.authenticated_message_shards||0)+'/4 份消息分库；历史完整性待核实。附件正文未读取。'+(h.last_error?' 错误：'+h.last_error:'');$('history-stop').disabled=!h.running;$('history-summary').disabled=!c.stored_messages;",
    "$('wechat-status').textContent=d.bridge.message;$('wechat-card').className='status-row '+(d.bridge.logged_in?'ok':'warn');": "$('wechat-status').textContent=d.database_inbox.running?'已登录客户端 · 本机数据库持续监听 · 自动发送待接通':d.bridge.message;$('wechat-card').className='status-row '+(d.database_inbox.running?'ok':'warn');",
    "$('receive-stop').onclick=": "$('history-summary').onclick=()=>action(async()=>{$('history-summary').disabled=true;toast('本机 Codex 正在总结真实群聊…');try{const j=await api('/api/history/summary',{});await waitJob(j.job_id);toast('真实群聊总结已生成，见右侧草稿')}finally{$('history-summary').disabled=false}});$('history-stop').onclick=()=>action(()=>api('/api/history/stop',{}));\n$('receive-stop').onclick=",
}
for before,after in changes.items():
    if html.count(before)!=1:raise ValueError('Console source differs: '+before[:50])
    html=html.replace(before,after)
path.write_text(html,encoding='utf-8')
script=html.split('<script>')[1].split('</script>')[0]
(root/'.local/console-check.js').write_text(script,encoding='utf-8')
print('Console updated')
