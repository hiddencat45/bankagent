# 有度 · 银行 AI 智能体

> **听得懂人话，但钱的事它说了不算。**

面向个人银行业务的对话式 AI 智能体。它直面的核心矛盾是：**模型能理解人的意图，却不能为资金决策负责。**

---

## 一、当前进度：先读这一段

**这是一个教学原型，不是可用的银行应用。** 代码里真正跑通的只有**余额查询**和**转账主链路**（准备 → 确认/强认证 → 执行 → 回复），而且集中在一个平面文件里，后端是内存模拟。

| 能力 | 代码状态 |
|---|---|
| 余额查询 | 已实现（教学版） |
| 智能转账 | 已实现主链路；后端为内存计算，**不落账、无幂等键、无事务** |
| 账单分析、理财操作、卡片管理、订阅与代扣、跨场景联动 | **设计目标，尚未实现** |
| 固定演示数据与一致性校验 | 已实现内部数据模块：两账户、联系人、七笔交易；**尚未接入图、API 或模型** |
| `preparaion/scenarios/`、`preparaion/bank_backend.py`、`api/`、`frontend/` | **尚未实现** |
| 真实模型接入、多轮槽位补全 | **未实现**；当前意图理解是离线规则（关键词 + 正则） |

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

门禁基线（2026-10-18 验证）：**11 条测试全绿、`pip check` 无冲突**。敏感字段扫描会列出教学占位符 `demo-otp-ok`，属已知的待改项，不判失败。

数据模块增量（2026-10-19 验证）：新增 17 条数据测试，完整门禁 **28 passed**、依赖检查通过。pytest 缓存目录可能报告权限警告，不影响测试结果。

若本机执行策略拦截 `.ps1`（提示「未对文件进行数字签名」）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

### 单独跑测试与教学 Demo

```powershell
cd preparaion
..\.venv\Scripts\python.exe -m pytest -q                        # 11 passed
..\.venv\Scripts\python.exe -X utf8 bank_agent_graph.py
```

Demo 实际输出：

```text
当前可用余额为 5000.00 CNY。
```

### 固定数据（供后续模拟后端加载）

在 `preparaion/` 下可执行：

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests/test_demo_data.py
```

Python 内部调用 `from data.generator import build_demo_data`，再调用 `build_demo_data()` 得到新的独立数据集，生成时先运行一致性校验。也可从 `data.validate` 导入 `validate_demo_data` 校验修改后的数据；非法金额、外键、时间或账本余额会抛 `ValueError`。

固定参考日是 2026-10-18，金额为整数分；account-001 余额 500000 分、消费合计 100000 分，account-002 是独立用户的数据。重复扣款真值不写入业务行。此模块不写文件、不扣款、不访问真实银行，也不提供 API 重置；后续后端可重新构建数据集，运行时全量重置仍须按接口契约同步使旧会话和授权失效。内部数据含账户归属，不能直接返回给模型或页面。

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
    ├─ bank_agent_graph.py        # 教学源码：State + 全部节点 + 图组装
    ├─ test_bank_agent_graph.py   # 11 条流程与安全测试
    ├─ data/                     # B：固定样例生成与账本一致性校验
    ├─ tests/test_demo_data.py    # B：17 条数据测试
    ├─ build_bank_agent_deck.js   # PPT 生成脚本（PPT 的真正源头）
    ├─ build_frontend_mockup.js   # 前端效果图生成脚本
    ├─ assets/                    # 全流程图的 Mermaid 源与 SVG/PNG 导出
    └─ 银行AI智能体全流程规划.pptx  # 交付物成品（由脚本生成）
```

规划中的目标结构（**尚未实现**）：`preparaion/bank_types.py`、`preparaion/scenarios/`、`preparaion/bank_backend.py`、`api/`、`frontend/`。

---

## 六、已知限制与未完成项

- 代码仍是**平铺单文件**，尚未按场景模块化（阶段 1 的工作）。
- **恢复路径读 `resume` 载荷**判断授权（`auth_token == "demo-otp-ok"`），违反「授权结果必须来自服务端查询」，必须改。
- 金额用 `float`，Checkpoint 用 `InMemorySaver`，**进程重启即丢**。
- 教学代码的通讯录是**精确姓名匹配**，没有重名、别名或手机号尾号歧义处理。
- 未实现多轮槽位补全：只回复「300 元」不会与上一轮的「给张伟转钱」自动合并。
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
