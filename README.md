# 有度 · 银行 AI 智能体

> **听得懂人话，但钱的事它说了不算。**

面向个人银行业务的对话式 AI 智能体。它直面的核心矛盾是：**模型能理解人的意图，却不能为资金决策负责。**

---

## 一、当前进度：先读这一段

**这是一个教学原型，不是可用的银行应用。** 从现有教学图入口（`bank_agent_graph.py`）跑通的仍是**余额查询**和**转账主链路**（准备 → 确认/强认证 → 执行 → 回复）。

阶段 1 的公共部分已有实现，尚待审查确认与集成验收，分别在三张待复核的 PR 里：

| PR | 内容 |
|---|---|
| #11 | 场景注册器 `scenarios/__init__.py` + 转账场景 `scenarios/transfer.py` |
| #12 | 安全层 `agent_security.py`：操作哈希、挑战/授权表 |
| #13 | 主图 `agent_graph.py`：把注册器、安全层、后端串成工作流 |

**三张 PR 都还没合并**（无复核），所以 `main` 上暂时看不到这些文件。按契约 §3.2，旧教学图 `bank_agent_graph.py` 保持原样不动，新旧并存。

| 能力 | 代码状态 |
|---|---|
| 余额查询 | 已实现（教学版） |
| 智能转账 | 教学版主链路可用；**新链路**（PR #11–#13）已实现整数分、操作哈希、服务端授权、幂等 |
| 账单分析 | 场景适配（B）已实现，**已由注册器发现并接入新主图**；尚无 API 出口 |
| 公共类型与模拟后端 | 已实现并已合入 `main` |
| 固定演示数据与一致性校验 | 已实现并已合入 `main` |
| 公共场景注册器、安全层、主图 | **已实现，待在 PR #11–#13 复核合并** |
| 理财操作、卡片管理、订阅与代扣、跨场景联动 | **设计目标，尚未实现** |
| `api/`、`frontend/` | **尚未实现** |
| 真实模型接入、多轮槽位补全 | **未实现**；当前意图理解是离线规则（关键词 + 正则） |

### 新主图做到了什么

- **候选不是参数**：`scenario`/`intent`/`candidate_params` 都是未受信任输入，`operation` 与 `params` 由 Python 依据注册器声明生成，`contact_id` 只能来自受控后端查询
- **resume 不是授权**：恢复后只读服务端挑战记录，不读 `decision`、不读任何口令字段（旧教学图的固定口令问题已在新链路消除）
- **状态如实映射**：后端 `REJECTED`/`FAILED` 不会被标成 `COMPLETED`；风险评估失败按失败关闭处理
- **一句话命中多个操作时要求澄清**，不按模块顺序猜

但它**还没有 API**：目前只能通过 Python 调用图，没有 HTTP 入口、没有 SSE、没有页面。

`preparaion/银行AI智能体全流程规划.pptx`（34 页）描述的是**设计目标**，其中只有转账主链路已在代码里落地。
**PPT 里写了 ≠ 代码里有。** 讨论、评审、写文档都不要把两者混为一谈。

---

## 二、四条核心能力

按「理解 → 决策 → 把关 → 追溯」排列：

1. **自然语言理解** —— 提取业务意图与候选参数，信息不足主动追问
2. **决策与执行分离** —— 模型只产出候选；金额计算、风险分级、白名单校验、操作哈希绑定由确定性代码负责
3. **人工把关** —— 写操作先出确认卡，高风险触发强认证，参数改动需重新确认
4. **全程可回溯** —— 图状态可暂停可恢复，结果只采信后端事实

覆盖六个目标场景：智能转账、账单分析、理财操作、卡片管理、订阅与代扣、跨场景联动。

---

## 三、安全边界（与目录结构无关，立即生效）

- **模型只产出候选**：候选意图与候选槽位不得直接成为可信 ID 或执行参数，执行决策由 Python 做。
- **服务端专属字段**，模型与前端一律不可写：
  `user_id`、`account_id`、`contact_id`、`risk_level`、`operation_hash`、`challenge_id`、`authorized`、`balance`、`result`
- **写操作必须命中白名单**，否则一律 DENY；`risk_level` 缺失或非法要报错，不得静默放行。
- **`interrupt()` 之前不得有任何不可重复的副作用**（发短信、扣款、生成流水号）——含 `interrupt` 的节点恢复时会从函数开头重新执行。
- **金额用 `Decimal` 或整数分**（`amount_minor`），禁止 `float`；现有教学代码的 `float` 只作迁移基线，不复制到新代码。
- **授权/认证结果必须来自服务端查询**，不得从 `Command(resume=...)` 载荷或模型参数读取。现有代码里的 `demo-otp-ok` 是教学占位符，**不是**生产认证，必须改。
- **敏感字段不进入** Prompt、ToolMessage、Checkpoint、日志、向量库、示例数据。

---

## 四、环境与运行

### 前置

Windows + **Python 3.10**（本机验证 3.10.9）+ PowerShell。

### 搭环境与门禁

```powershell
.\scripts\setup.ps1     # 建 .venv、升级 pip、按 requirements.txt 装锁定版本
.\scripts\check.ps1     # 门禁：pytest + 敏感字段扫描 + pip check
```

门禁基线（`main`，2026-10-19 验证）：**100 passed**（11 条教学回归、23 条类型测试、17 条数据测试、24 条后端测试、25 条账单适配测试），`pip check` 无冲突。pytest 缓存目录可能报告权限警告，不影响测试结果。

阶段 1 分支叠加后（`feat/graph-integration`，含 PR #11–#13）：**272 passed**（2026-10-20 修复后）。新增部分为注册器 31 条、转账场景 43 条、安全层 31 条、安全层与后端集成 14 条；另补金额、余额、否定写请求及异常边界回归。

敏感字段扫描会列出教学占位符 `demo-otp-ok`（仅存在于旧教学图 `bank_agent_graph.py` 与其测试中），属已知的待迁移项，不判失败；新链路不使用任何固定口令。

若本机执行策略拦截 `.ps1`（提示「未对文件进行数字签名」）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

### 单独跑测试与教学 Demo

```powershell
cd preparaion
..\.venv\Scripts\python.exe -m pytest -q test_bank_agent_graph.py # 原教学 11 条
..\.venv\Scripts\python.exe -X utf8 bank_agent_graph.py
```

Demo 实际输出：

```text
当前可用余额为 5000.00 CNY。
```

### 新主图（需先合并 PR #11–#13）

```powershell
cd preparaion
..\.venv\Scripts\python.exe -m pytest -q tests/test_agent_graph.py
```

服务端内部装配示例：客户端只提供消息；user_id/account_id 来自服务端登录会话，request_id 由服务端生成。以下虚构身份仅用于本地 Python 演示：

```python
import threading
from datetime import datetime
from langgraph.types import Command

from agent_graph import BankAgentRuntime, build_graph
from agent_security import SG_TZ, ChallengeStore, compute_operation_hash
from bank_backend import configure_backend
from data.generator import build_demo_data
from scenarios.bills import configure_clock

lock = threading.RLock()
clock = lambda: datetime(2026, 10, 18, 10, 0, tzinfo=SG_TZ)   # 与演示数据参考日对齐
configure_clock(clock=clock)
store = ChallengeStore(lock=lock, clock=clock)
configure_backend(
    data_factory=build_demo_data,
    lookup_authorization=store.lookup,
    operation_hash=compute_operation_hash,
    lock=lock,
    clock=clock,
)

graph = build_graph(BankAgentRuntime(challenges=store, clock=clock))
cfg = {"configurable": {"thread_id": "conv-1"}}

out = graph.invoke({
    "user_id": "user-001", "account_id": "account-001",
    "request_id": "req-1", "message": "给张伟转 300 元",
}, cfg)
# out["__interrupt__"] 里是确认卡；写操作不会在这里扣款

# 用户在页面上确认后，服务端先落授权记录，再恢复图：
intr = out["__interrupt__"][0].value
store.decide(challenge_id=intr["challenge_id"], user_id="user-001", request_id="req-1",
             operation_hash=intr["operation_hash"], decision="approve")
final = graph.invoke(Command(resume={"decision": "approve"}), cfg)
print(final["status"], final["response"])
```

**注意**：`Command(resume=...)` 里的内容不是授权凭证。恢复时图只查 `ChallengeStore`，所以必须先由服务端写入授权记录；客户端伪造 `approve` 不会扣款。

### 独立模拟后端（已接新主图，待 API）

在 `preparaion/` 下运行 `..\.venv\Scripts\python.exe -m pytest -q tests/test_bank_backend.py` 可验证隔离后端。测试使用独立小样例和服务端授权替身，不要求先运行 API，也不代表真实认证已接入。

服务端启动时调用 `bank_backend.configure_backend(...)` 一次，注入已校验的 `data_factory`、`lookup_authorization(ref)`、`operation_hash(context, operation, params)`、共享 `threading.RLock` 以及可选 `clock()`。固定日期演示应让 clock 与数据参考日一致；不注入时使用真实当前时间。返回的 `BankBackend` 实例和模块级 get_balance/find_contacts/query_bills/execute_transfer/reset_demo_data 入口操作同一份内存数据。图与 API 不得从客户端构造这些依赖；未配置时入口报错，无授权查询或哈希函数时转账拒绝。

授权表的终态修改、后端写入及 API 的整体验示重置必须使用同一个 RLock；重置业务数据后，A 仍须在该锁内使旧会话、授权和 Checkpoint 失效，不能把后端 reset 当作完整的 /demo/reset。可用下面数据模块的 build_demo_data 作 data_factory，此后端本身不导入数据包或图模块。

后端全部使用整数分；重复成功操作返回原结果，失败不扣款，累计风险在锁内复查。余额结果含内部风控累计值，A 对外序列化前必须按 SERVER_ONLY_DATA_FIELDS 过滤；不能直接送模型或 SSE。进程重启丢失内存账本、幂等缓存和授权；没有连接真实银行，也不宣称外部收款到账。

联系人解析的 `find_contacts` 在归属失败时按契约抛 `PermissionError`；A 在公共 resolve 调用边界统一转成当前操作的 REJECTED/ACCOUNT_NOT_ACCESSIBLE，不能当成空联系人继续执行。

### 固定数据（供模拟后端加载）

在 `preparaion/` 下可执行：

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests/test_demo_data.py
```

Python 内部调用 `from data.generator import build_demo_data`，再调用 `build_demo_data()` 得到新的独立数据集，生成时先运行一致性校验。也可从 `data.validate` 导入 `validate_demo_data` 校验修改后的数据；非法金额、外键、时间或账本余额会抛 `ValueError`。

固定参考日是 2026-10-18，金额为整数分；account-001 余额 500000 分、消费合计 100000 分，account-002 是独立用户的数据。重复扣款真值不写入业务行。此模块不写文件、不扣款、不访问真实银行，也不提供 API 重置；后续后端可重新构建数据集，运行时全量重置仍须按接口契约同步使旧会话和授权失效。内部数据含账户归属，不能直接返回给模型或页面。

### 账单适配层（已由注册器发现并接入新主图）

`scenarios/bills.py` 提供已约定的 SCENARIO、INTENTS、resolve、validate、execute、render。支持本月、上月、近 N 天（1–366），缺省本月；非法期间不退回默认值。服务端可用 `configure_clock(clock=...)` 注入与后端一致的带时区时钟，固定演示时必须对齐参考日期；不改变 TrustedContext 或 State。

`scenarios/__init__.py` 通过 `pkgutil` 自动发现 `scenarios/` 下的场景模块并校验其声明，**B 新增场景不需要改注册器**。B 的文件没有做任何修改。

在 `preparaion/` 执行 `..\.venv\Scripts\python.exe -m pytest -q tests/test_bills_scenario.py` 可验证日期边界、实际后端调用、跨用户拒绝和证据回复。端到端路径（识别 → 解析 → GREEN 策略 → 执行 → 渲染）由 `tests/test_agent_graph.py` 覆盖；页面展示仍未实现。

### 两个已经踩过的坑

1. **Python 3.10 自带的 pip 是 22.3.1**，其依赖解析器会在 `langgraph` 上疯狂回溯：CPU 跑满、pip 缓存涨到几百 MB，但 `site-packages` 一个包都装不上。**必须先 `pip install --upgrade pip`**（升到 26.x 后秒装）。
2. **国内直连 PyPI 极慢**，加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`。

`scripts/setup.ps1` 已把这两条封装好，优先用它，不要手敲 `pip install`。

---

## 五、目录结构

当前真实存在（`preparaion` 是 `preparation` 的拼写错误，本轮保留，不要擅自改名）：

```text
bankagent/
├─ AGENTS.md                      # 全局安全边界、Git 约定、目录所有权、完成标准
├─ README.md                      # 本文件
├─ requirements.txt               # 依赖，完全锁定
├─ scripts/
│   ├─ setup.ps1                  # 一键搭环境
│   └─ check.ps1                  # 一键门禁
├─ docs/
│   ├─ 协作方案.md                 # 阶段 0–4、接口确认流程、任务卡模板、合并与检查
│   ├─ 场景扩展与分工.md           # 场景模块契约、操作声明、统一结果结构
│   └─ 阶段0-接口草案.md           # 阶段 0 接口草案（过渡文件，阶段 1 落地后由代码取代）
└─ preparaion/
    ├─ bank_agent_graph.py        # 旧教学源码：State + 全部节点 + 图组装（契约 §3.2 暂不改）
    ├─ agent_graph.py             # A：新主图，串联注册器、安全层与后端（PR #13）
    ├─ agent_security.py          # A：操作哈希、挑战与授权表（PR #12）
    ├─ bank_types.py              # 已确认的公共类型和常量
    ├─ bank_backend.py            # B：内存查询与受控转账，不依赖图
    ├─ scenarios/
    │   ├─ __init__.py            # A：场景注册器，自动发现并校验场景声明（PR #11）
    │   ├─ transfer.py            # A：转账场景（PR #11）
    │   └─ bills.py               # B：账单场景适配
    ├─ test_bank_agent_graph.py   # 旧教学图的 11 条流程与安全测试
    ├─ data/                      # B：固定样例生成与账本一致性校验
    ├─ tests/                     # 类型、固定数据、后端、注册器、安全层、主图测试
    ├─ build_bank_agent_deck.js   # PPT 生成脚本（PPT 的真正源头）
    ├─ build_frontend_mockup.js   # 前端效果图生成脚本
    ├─ assets/                    # 全流程图的 Mermaid 源与 SVG/PNG 导出
    └─ 银行AI智能体全流程规划.pptx  # 交付物成品（由脚本生成）
```

尚未实现：`api/`、`frontend/`，以及理财、卡片、订阅与代扣、跨场景联动四个场景。

---

## 六、已知限制与未完成项

- 旧教学图仍为单文件；新主图 `agent_graph.py` 已实现但**尚未合并**，两者暂时并存。
- **恢复路径读 `resume` 载荷**判断授权（`auth_token == "demo-otp-ok"`）这一缺陷**仅存在于旧教学图**；新主图已改为只读服务端记录，但旧图按契约 §3.2 暂不改，需专门的阶段 1 迁移 PR。
- 旧教学图金额仍用 `float`；新链路用整数分（`amount_minor`）。新主图同样使用 `InMemorySaver`，**进程重启即丢 Checkpoint**；内存后端也不落账。
- 旧教学代码的通讯录是**精确姓名匹配**，没有重名、别名或手机号尾号歧义处理。新转账场景解析同样拒绝猜测：重名时要求澄清，不会自动挑一个。
- **没有 API 层**：`POST /agent/chat`、SSE 事件、`/health`、`/demo/reset` 都还没写，目前只能直接调用图。
- **意图识别是离线规则**（注册器关键词 + 正则），没有接真实模型。
- 未实现多轮槽位补全：只回复「300 元」不会与上一轮的「给张伟转钱」自动合并。图内已按 `(user_id, thread_id)` 记录 30 分钟澄清期限，但把新值合并进上一轮候选需要 API 层传 `pending` 上下文，该部分未做。
- PPT 生成脚本依赖**仓库外**的本机 `.dsh` 路径，队友 clone 后跑不了 PPT 生成；**绝不手改 PPTX**，手改会在下次生成时被覆盖。
- 产品名「有度」尚未落到 PPT 与前端样稿（封面仍是「银行 AI 智能体 · 全流程规划」）。改名必须改生成脚本后重新生成。
- 比赛官方细则、评分口径、截止日期与演示时长**尚未核实**；模型供应商、模型与凭据**尚未确定**——这两项不阻塞开发，但提交前必须核对。

---

## 七、协作方式

双人开发，规则以仓库内文档为准，**不要凭记忆推断**：

| 文件 | 管什么 |
|---|---|
| `AGENTS.md` | 全局安全边界、Git 约定、目录所有权、完成标准 |
| `docs/协作方案.md` | 阶段 0–4、接口确认流程、任务卡模板、合并与检查 |
| `docs/场景扩展与分工.md` | 场景模块契约（4 必需 + 4 可选钩子）、操作声明、统一结果结构 |
| `docs/阶段0-接口草案.md` | 阶段 0 接口草案：公共状态、场景接口、API、SSE 事件 |

| | 人 | 工具 | 领地 |
|---|---|---|---|
| A | （本仓库主） | DSH | 公共图与调度、安全、转账与卡片场景、`api/`、模型适配与多轮补全、README、PPT 与答辩 |
| B | Zason42 | Codex | 模拟后端与数据、账单/订阅/理财场景、`frontend/` |

- 分支命名：`feat/`、`fix/`、`docs/`、`refactor/`、`contract/`；**一个任务 = 一个分支 = 一个 PR**，diff 尽量 < 400 行。
- commit 格式：`<类型>(<范围>): <中文简述>`。
- **不许直接推 `main`**；合并前 `pytest` 全绿 + 对方确认，**并核对 PR 头 SHA 与已审查的那个一致**。
- 修改公共 State、后端公开签名、操作声明或结果结构属**契约变更**，必须走 `contract/<简述>` 分支并由双方确认。
- 改别人领地的文件前先说一句；任务已明确授权跨目录修改则无需重复询问。

做完一个任务的标准见 `AGENTS.md` 第八节：`.\scripts\check.ps1` 全绿、新增行为有**会真正失败**的测试、没越界、没声称实现了不存在的能力。
