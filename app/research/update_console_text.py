"""One-time replacement of stale prototype explanations after native intake."""
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'index.html'
text=path.read_text(encoding='utf-8')
replacements={
    '<h3>连接真实微信群</h3>':'<h3>群消息接收</h3><p id="receive-status" class="muted">正在读取接收状态…</p><button id="receive-stop" disabled>停止接收观测</button><h3>群聊记忆</h3><p id="history-status" class="muted">正在读取本机记录范围…</p><h3>连接真实微信群</h3>',
    '原生观察器支持持续运行，无需赶测试窗口。在电脑微信的「示例工作群」发送 WXPAIR1006 即可留下测试样本。退出微信或停止观测后结束；真实群自动回复尚未接通。':'当前通过已登录的电脑微信研究原生收发。发送样本已取得；接收和历史读取按实际验证结果显示。微信退出后观察器结束。',
    '启动时跳过已有历史消息':'历史 @ 导入时不触发旧提问',
    '仅记录助手参与的对话 · 不读取全部聊天历史':'目标群本机记录 · 历史覆盖范围待验证',
    '连接成功后，启动时已有的消息会被跳过。只有新出现且 @ 助手的文本会交给模型。':'已验证的目标群文本会保存到本机，包含普通讨论。新 @ 消息才调用模型；历史导入不触发旧提问。',
}
for before,after in replacements.items():
    if text.count(before)!=1:raise ValueError('Expected unique console text: '+before)
    text=text.replace(before,after)
path.write_text(text,encoding='utf-8')
