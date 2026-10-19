# 前端接入（开发中）

当前交付是面向浏览器的 POST/SSE 通信模块，还没有页面或可运行的端到端 Demo。
依据已确认的 `docs/阶段0-接口草案.md` §4.1–4.3；不依赖尚未合并的 A 分支。

`agent-client.mjs` 使用标准 fetch 与 ReadableStream，不新增第三方依赖：

- `createAgentClient().send(request, {token, onEvent, signal})` 向同源 `/agent/chat` 发送请求。
- request 只允许 `thread_id/message/resume`；可信身份由服务端注入。
- token 必须来自服务端发放的演示会话，仅短暂传入，不写浏览器持久存储或日志。
- onEvent 接收 `{event, data}`，data 为六种已确认事件的信封。
- 第一条事件必须为 status；一轮的 thread_id/request_id/mode 必须一致。
- done 的业务状态原样保留，等待确认、澄清、拒绝和失败都不转换为成功。
- 断流、取消或协议异常会抛 AgentClientError；不会自动重发 POST。
- 同一个客户端实例的并发发送被拒绝；服务端仍须实现 RUN_BUSY 和写入幂等。

验证（使用支持 fetch/ReadableStream 的 Node.js，开发机已用 Node 24 验证）：

```powershell
node --test frontend/tests/agent-client.test.mjs
.\scripts\check.ps1
```

测试替身仅在测试中返回合成事件，不是运行时模拟银行响应。
现有 scripts/check.ps1 只运行 Python 门禁；前端测试须单独运行上述 node 命令。
目前已在 Node 验证流读取与请求行为，尚未完成真实浏览器和 HTTP 服务联调。

后续接入：A 提供受控演示会话入口及响应格式、实际 HTTP 服务；B 在此模块上增加
账单证据、转账确认卡与执行轨迹的页面。卡片字段校验、挑战一致性、过期、按钮状态和
金额展示由页面层实现。OTP 只能短暂传给 resume，消费后清空，不能写入对话记录。
通信模块没有验证卡片业务 payload，也不替代服务端授权、归属和金额校验。
