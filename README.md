# Mydex 微信助手

群内真实 @ 回复、私聊新消息回复，使用千问 Qwen3.8-Flash；按会话排队，共享 4 路模型并发。

- [新电脑接手提示词](deployment/NEXT-AGENT-PROMPT.txt)
- [完整交接说明](deployment/HANDOFF.txt)
- [双电脑协作流程](deployment/COLLABORATION.txt)
- [公开版说明](PUBLIC-EDITION.txt)

公开版已将真实账号、群 ID 和机器信息替换为示例；不包含密钥、凭证、聊天记录、运行状态或私有 Git 历史。原生组件已按公开源码重新编译。部署时必须重新认证本机账号，不能直接使用示例 ID。

入口为 `app/account_assistant.py`。小电脑环境已准备；35 项测试及独立原生发送夹具通过。目标机器的微信登录、API 本地配置、账号绑定和实际收发仍需完成。原生引用发送仍在研究。
