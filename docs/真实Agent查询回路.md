# 首条真实 Agent 查询回路

## 范围与当前证据

本次接通原生 function calling：模型选择只读工具 → 后端执行 → tool 消息反馈实际结果 → 模型继续调用或自然回答。支持同一请求内多个查询，以及“最近钱花在哪里 → 只看餐饮 → 列出超过一百的”的跨轮筛选。

协议依据：[DeepSeek Tool Calls](https://api-docs.deepseek.com/guides/tool_calls/)。通过已有 httpx 适配器发送 tools 与 messages，不新增 SDK。离线模式保持原行为，不把离线或测试替身称为真实模型成功。

自动化使用确定性的模型替身/MockTransport与真实内存银行后端，不证明实际供应商的语言理解效果。真实模型验收使用 scripts/check_query_model.py，需本机配置凭据；未运行通过前不能宣称完成真实供应商验收。

## 2026-10-26 真实模型验收记录

在代码提交 `82693a046fdfa2800b0ee19f42062cf162d4877a` 上运行 `scripts/check_query_model.py`，使用本机配置凭据及默认模型 `deepseek-flash`，退出码为 0。本次仅执行查询，没有资金操作，也未将凭据写入仓库。

| 连续输入 | 后端结果 | 耗时 |
|---|---|---|
| 最近钱花在哪里了 | 100,000 分，5 笔消费 | 2.27 秒 |
| 只看餐饮 | 12,000 分，1 笔消费，类别为餐饮 | 2.17 秒 |
| 列出超过一百的 | 12,000 分，1 笔消费，保留餐饮并添加严格大于 10,000 分条件 | 1.69 秒 |

脚本校验了同一会话中的 COMPLETED 状态、QUERY_BILLS 回执、金额及类别/金额条件继承。本次是一次三轮真实调用结果，不代表重复运行成功率、全部自然表达或模型措辞准确性已全面验收；未执行浏览器视觉验收。后续提交仅记录此证据，业务代码未变化。

## 契约增量

- `OpenAICompatibleModel.complete_tools(messages, tools, require_tool=False, timeout=30)` 返回供应商 assistant message。原有 predict/health 接口保留，非查询场景继续使用原候选路径。
- `create_app`、`Service`、`BankAgentRuntime` 增加服务端 `query_model` 注入。只传 candidate_model 的旧测试/集成仍验证旧候选边界；正式 create_demo_app 自动把已配置模型同时接入两条路径，不在工具调用失败后回退。
- 新只读后端 `query_expenses(context, start, end, category=None, merchant=None, amount_gt_minor=None)` 返回现有 QUERY_BILLS/BackendResult，新增 data.filters。只算 EXPENSE，金额为整数分；类别精确匹配，商户按子串匹配，金额严格大于；按时间及交易引用排序。
- 筛选在条数限制之前执行。匹配结果超过100条明确拒绝，不以截断数据冒充完整汇总。日期左闭右开，最长366天；当前业务日期仍由模拟后端时钟提供。
- BankAgentState 新增 `query_results`，保存本轮完成的只读结果，下一轮清空。SSE 继续使用现有 evidence/result 卡，逐项展示本轮成功结果；金额、日期与筛选条件由后端确定性展示。
- 查询条件与授权分离：QueryAgent 在服务端按用户、账户、thread 保存最近一次完整成功查询，30分钟失效，重置和进程重启清除。不把长期聊天记忆或持久化提前纳入本次。

## 工具与边界

| 工具 | 用途 |
|---|---|
| query_expenses | 消费汇总和明细；inherit=true 继承，显式字段替换，null 清空；新查询 inherit=false 默认近30天 |
| get_balance | 当前登录账户余额；不接收身份参数 |
| ask_user | 缺信息或能力说明，不产生业务结果 |
| handoff_banking | 交回原有转账、卡片等处理流程，不执行、不授权 |

查询路径在关键词预判前交给模型。其他业务经 handoff_banking 后仍走原确认、安全和幂等流程；这不是复杂写任务编排的完成。本轮不支持同时混合查询和写操作的工具计划，明确失败而不静默丢弃其中一部分。

模型不能提供 user_id、account_id、授权字段或任意函数名。余额工具只向模型投影余额和币种，不泄露风控累计值。工具结果、历史与商户文本不是指令。错误或拒绝结果由程序决定状态，不让模型改写为成功。

回路最多5轮模型响应、6次工具调用，45秒预算；网络请求受剩余预算及供应商超时约束，响应回来后再次检查预算。不执行模型生成的代码，不开放写工具。最终自然语言是模型解释，不作为账务或授权依据；业务卡片才是后端结果。仍需真实模型评估措辞准确性。

## 运行与验证

在配置模型环境变量的终端、仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe scripts/check_query_model.py
.\.venv\Scripts\python.exe -m uvicorn frontend.dev_app:create_app --factory --app-dir src --host 127.0.0.1 --port 8021 --workers 1 --no-access-log
```

check_query_model 使用独立进程内数据，连续查询三轮并核对汇总和筛选条件，不发起资金操作。默认供应商/模型沿用现有配置，最终产品选型仍未冻结。

自动化覆盖原生请求/响应、工具结果再反馈、跨轮继承与重置、空结果、金额边界、用户/账户/会话隔离、过期与重置、未知工具和越权参数、模型失败、调用限制及转账确认回归。浏览器视觉验收与真实供应商验收分别记录，不用替身替代。