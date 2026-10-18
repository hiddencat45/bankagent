# assets · 全流程图素材

本目录存放讲课用图的**源文件**与**导出物**。源文件是唯一真相，导出物可随时重生成。

## 文件

| 文件 | 角色 |
|---|---|
| `langgraph-full-flow.mmd` | 唯一源文件。Mermaid `flowchart TB`，含 28 个节点、4 个阶段子图、17 条边，标注每个节点的 `IN / READ / OUT(ΔState)`。 |
| `langgraph-full-flow.svg` | 由 `.mmd` 导出的矢量图，第 7 页 PPT 上的超链接指向它。 |
| `langgraph-full-flow.png` | 同一张图的位图导出（1568 × 9247 px，已裁掉四周空白），给不便看 SVG 的场景用。 |
| `puppeteer.json` | 让 mermaid-cli 复用本机 Chrome、不额外下载 Chromium。 |

## 重新生成

改完 `.mmd` 后按下面两条命令重导（`mmdc` 即 mermaid-cli）：

```powershell
# 1) 安装一次（约 194 个包，Chromium 用系统已装的 Chrome，不额外下载）
$env:PUPPETEER_SKIP_DOWNLOAD = "true"
npm install @mermaid-js/mermaid-cli

# 2) 导出。puppeteer.json 里指定本机 Chrome 路径，避免下载 Chromium
mmdc -i langgraph-full-flow.mmd -o langgraph-full-flow.svg -p puppeteer.json -b white
mmdc -i langgraph-full-flow.mmd -o langgraph-full-flow.png -p puppeteer.json -b white -s 2
```

`puppeteer.json` 内容：

```json
{
  "executablePath": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "args": ["--no-sandbox", "--disable-dev-shm-usage"]
}
```

注意：该文件必须**不带 BOM**。用 PowerShell 5.1 的 `Set-Content -Encoding UTF8` 会写入 BOM，导致 mermaid-cli 报
`SyntaxError: Unexpected token '\uFEFF'`；请改用
`[System.IO.File]::WriteAllText($path, $json, (New-Object System.Text.UTF8Encoding($false)))`。

## 与源码的对应关系

图对应 `../bank_agent_graph.py` 的 `build_graph()`（第 470–567 行）。要改图，先改代码，再核对这几处：

- 节点名与 `add_node` 的字符串必须一致（图里多出的 `RC / RI / RPLAN / RSEC / RAC / RAA` 六边形是**路由函数**，不是用 `add_node` 注册的节点）。
- 边的标签对应 `add_conditional_edges` 的 path map 键名。
- `RAC` 与 `RAA` 是**同一个** `route_authorization` 被注册了两次，分别接在黄色与红色中断之后。
- 澄清路径 `ask_clarification → END` 走的是 `add_edge`，不是 `interrupt`；下一轮是同一 `thread_id` 的新一次 `graph.invoke`。
