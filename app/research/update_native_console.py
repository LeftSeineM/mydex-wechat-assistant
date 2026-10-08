"""Show the verified native path and its continuous reply controls."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'index.html'
html=path.read_text(encoding='utf-8')
pairs=[
('已登录客户端 · 本机数据库持续监听 · 自动发送待接通', '已登录客户端 · 持续监听 · '+"'+(d.native_sender.connected&&d.native_sender.enabled?'@ 自动回复已开启':'自动回复已暂停')+'"),
("'目标群真实记录 · @ 回复目前生成本机草稿'", "'目标群真实记录 · '+(d.native_sender.enabled?'真实 @ 自动回复':'回复先保存在草稿')"),
("sent:'库报告已发送'", "sent:'已核对真实群发送记录'"),
("b.disabled=!d.bridge.running", "b.disabled=!d.native_sender.connected||!d.native_sender.enabled||draft.source!=='wechat'||!draft.event_id"),
("await api('/api/outbox/send',{id:draft.id});toast('草稿已进入发送队列')", "const j=await api('/api/native/send',{id:draft.id});const r=await waitJob(j.job_id);toast(r.server_record_verified?'回复已发回真实群':'发送结果待核对')"),
("$('connect').textContent='原生发送研究中';$('auto-send').disabled=true;", "$('connect').textContent=state.native_sender.connected?'客户端原生通道已接通':'客户端连接待恢复';$('auto-send').disabled=!state.native_sender.connected;$('auto-send').checked=state.native_sender.enabled;"),
("$('bridge-status').textContent='新消息经验证后存入本机记录；@ 回复先生成草稿，自动发回群尚未接通。'", "$('bridge-status').textContent=state.native_sender.message+'。'+(state.native_sender.enabled?'成员通过微信选择 @示例账号 提问，回答自动发回本群。':'已暂停自动回复，草稿仍保存在本机。')+(h.last_send_error?' 上次发送：'+h.last_send_error:'')"),
("$('connect').onclick=()=>action(()=>api('/api/bridge/start',{auto_send:$('auto-send').checked}));$('stop').onclick=()=>action(()=>api('/api/bridge/stop',{}));", "$('auto-send').onchange=()=>action(()=>api('/api/native/sending',{enabled:$('auto-send').checked}));$('connect').onclick=()=>refresh();$('stop').disabled=true;"),
('当前通过已登录的电脑微信研究原生收发。发送样本已取得；接收和历史读取按实际验证结果显示。微信退出后观察器结束。','已通过电脑微信原生通道验证收发。本群新消息持续保存，成员真正 @ 当前账号时自动回答。电脑微信与本机服务需要保持运行。'),
]
for old,new in pairs:
    if html.count(old)!=1:raise ValueError('Unexpected UI source for '+old[:70])
    html=html.replace(old,new)
path.write_text(html,encoding='utf-8')
print('Native automatic-reply state and controls updated')
