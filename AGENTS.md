# AGENTS.md — 银行 AI 智能体（比赛项目）

> 本文件对 **DSH、Codex、Claude Code** 等所有 AI 助手生效。动手前先读完。
> 有冲突时以本文件为准；更具体的目录级约定优先于本文件。

---

## 一、项目是什么

银行 AI 智能体，覆盖 6 个场景：**智能转账、账单分析、理财操作、卡片管理、订阅与代扣、跨场景联动**。

交付物：**可运行 Demo（优先）+ 答辩 PPT**。

⚠️ **最重要的一条前提**：`银行AI智能体全流程规划.pptx`（34 页）描述的是**设计目标**，
其中只有**智能转账**主链路已在代码里实现，其余 5 个场景是设计意图。
**PPT 里写了 ≠ 代码里有。** 讨论、写文档、写代码时都不要把两者混为一谈。

---

## 二、当前状态（重构尚未进行）

代码目前是**平铺的单文件结构**，重构（拆分为分层结构）还没做：

| 现在的位置 | 内容 | 重构后的目标位置 |
|---|---|---|
| `preparaion/bank_agent_graph.py` | 教学源码，583 行，State + 全部节点 + 图组装 | `src/bankagent/contracts/` + `src/bankagent/graph/` |
| `preparaion/test_bank_agent_graph.py` | 11 条流程与安全测试 | `tests/` |
| `preparaion/build_bank_agent_deck.js` | PPT 生成脚本（**PPT 的真正源头**） | `deck/` |
| `preparaion/assets/` | 全流程图的 Mermaid 源与导出 | `deck/assets/` |
| `preparaion/银行AI智能体全流程规划.pptx` | 交付物成品（由脚本生成） | `release/` |

**目录名 `preparaion` 是 `preparation` 的拼写错误**，重构时会一并处理，暂时不要动它。

重构之外的目录（`src/`、`docs/`、`tests/`、`api/`、`scripts/`）**还不存在**，
本文件提到的这些路径都是**目标结构**，以"重构后的目标位置"一栏为准。

测试目前**跑不起来**：`langgraph` 未安装在当前 Python 环境。修环境是待办事项，不是"已经能用"。

---

## 三、绝对不要做

- 不要把 PPT 里的设计目标当成已实现能力去调用、断言或写文档
- 不要在同一个提交里同时做重构和加功能
- 不要新增第三方依赖，除非在 PR 描述里给出理由
- 不要为了"让代码跑通"而修改或放宽已有测试的断言
- 不要把密钥、口令、OTP、真实卡号、身份证号、手机号写进代码、测试、样例数据或日志
- 不要 `git push --force`、不要直接往 `main` 推（见第六节）
- 不要去动 `.git/` 目录

---

## 四、安全边界（立即生效，与结构无关）

这是在**转账链路**里已经论证过的结论，新写的任何场景都必须遵守：

- **模型只产出候选**：`intent`、`recipient_name`、`amount`。执行决策由 Python 做，不由模型做。
- **以下字段只能由服务端生成**，模型与前端一律不可写：
  `user_id`、`account_id`、`contact_id`、`risk_level`、`operation_hash`、
  `challenge_id`、`authorized`、`balance`、`result`
- **写操作必须命中白名单** `ALLOWED_OPERATIONS`，否则一律 DENY；`risk_level` 缺失或非法时应报错，不得静默放行
- **`interrupt()` 之前不得有任何不可重复的副作用**（发短信、扣款、生成流水号）。
  含 `interrupt` 的节点在恢复时**会从函数开头重新执行**，副作用必须移到中断之后。
- **资金运算用 `Decimal` 或整数分**，禁止用 `float`。
  现有教学代码用 `float` 只为缩短示例，新代码不要沿用。
- **授权/认证结果必须来自服务端查询**，不得从 `Command(resume=...)` 载荷或模型参数中读取。
  现有代码里的 `demo-otp-ok` 是教学占位符，**不是**生产认证。
- **敏感字段不进入** Prompt、ToolMessage、Checkpoint、日志、向量库。

---

## 五、目录所有权（目标结构，重构后生效）

| 路径 | 负责人 | 说明 |
|---|---|---|
| `src/bankagent/contracts/` | **共管** | 纯声明（State、枚举、工具签名），无逻辑。改动需两人确认 |
| `src/bankagent/graph/` | A | LangGraph 图、节点、路由、安全策略、中断与执行 |
| `src/bankagent/tools/` | B | 6 场景工具函数 |
| `src/bankagent/data/` | B | 模拟数据生成与一致性校验 |
| `api/` | B | FastAPI + SSE |
| `frontend/` | B | 演示工作台 |
| `deck/` | 共管 | PPT 生成脚本与流程图素材 |
| `tests/` | 各自 | 谁的功能谁写测试 |
| `docs/` | 共管 | 契约与看板 |

**改别人领地的文件前，先说一句。**

### 契约变更（待 `docs/contracts/` 建立后生效）

改 `docs/contracts/` 或 `src/bankagent/contracts/` 下任何文件：
1. 单独开 `contract/<简述>` 分支
2. PR 描述写明：改了什么、为什么必须改、影响哪些文件
3. 两人都确认才能合并

**任何 AI 助手都不许为了"让代码跑通"而自行修改契约。**

---

## 六、提交与协作规范（立即生效）

- 分支命名：`feat/<场景或模块>-<简述>`、`fix/<简述>`、`docs/<简述>`、`refactor/<简述>`、`contract/<简述>`
- commit 格式：`<类型>(<范围>): <中文简述>`
  - 例：`feat(tools): 增加账单分析三个工具`
  - 类型用 `feat` / `fix` / `docs` / `refactor` / `test` / `chore`
- **一个任务 = 一个分支 = 一个 PR，diff 尽量 < 400 行。**
  超过 400 行的 PR 人和 AI 都审不出问题，等于没审。
- **不要直接往 `main` 提交**（首次导入除外）。所有改动走 PR。
- 合并前必须：`pytest` 全绿 + 对方确认。

---

## 七、环境

- Python 3.10（与现有 `__pycache__` 里的 `cpython-310` 一致）
- 用 `.venv`，不要往全局环境装包
- 依赖版本固定后写入 `requirements.txt`（**尚未创建**）
- 一键检查脚本 `scripts/check.ps1`（**尚未创建**）

---

## 八、完成的标准

一个任务算完成，需要同时满足：

1. `pytest` 全绿（环境修好后）
2. 新增行为有对应测试，且测试**真的会失败**（不是恒真断言）
3. 没有擅自修改契约、没有越界改别人领地的文件
4. 没有声称实现了契约里没有、或 PPT 里有但代码里没有的能力

**AI 助手自己的判断，"完成"不算完成。**
做不到的部分写成 `TODO`，并在 PR 描述里说明，不要假装做到了。
