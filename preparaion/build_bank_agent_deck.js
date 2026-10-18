const pptxgen = require('../../.dsh/pptx-tools/node_modules/pptxgenjs');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'Banking Agent Project';
pptx.subject = '银行 AI 智能体全流程规划';
pptx.title = '银行 AI 智能体全流程规划';
pptx.company = 'Banking Agent Project';
pptx.lang = 'zh-CN';
pptx.theme = {
  headFontFace: 'Microsoft YaHei',
  bodyFontFace: 'Microsoft YaHei',
  lang: 'zh-CN'
};

const C = {
  navy: '173B5E', navy2: '244F73', teal: '178078', green: '2F8F63', amber: 'E2A62B',
  red: 'C94F48', purple: '7657A6', ink: '162534', muted: '64727F', line: 'D7DEE4',
  bg: 'F5F7F9', white: 'FFFFFF'
};
const S = pptx.ShapeType;

const slide = pptx.addSlide();
slide.background = { color: C.bg };

// 左侧深蓝区域用于建立稳重、可信的银行科技视觉印象。
slide.addShape(S.rect, {
  x: 0, y: 0, w: 4.0, h: 7.5,
  fill: { color: C.navy }, line: { color: C.navy }
});
slide.addShape(S.rect, {
  x: 0.56, y: 0.72, w: 0.52, h: 0.07,
  fill: { color: C.teal }, line: { color: C.teal }
});
slide.addText('BANKING AGENT', {
  x: 0.56, y: 0.92, w: 2.7, h: 0.28,
  fontSize: 11, bold: true, color: 'BFD2E1', charSpacing: 1.4, margin: 0
});
slide.addText('安全可信的\n自主执行', {
  x: 0.56, y: 1.7, w: 2.9, h: 1.3,
  fontSize: 29, bold: true, color: C.white, margin: 0, valign: 'mid'
});
slide.addText('LLM 提议 · Python 决策 · 银行后端执行', {
  x: 0.56, y: 3.28, w: 2.85, h: 0.6,
  fontSize: 11, color: 'D7E4EC', margin: 0
});

// 三个风险色点只作为体系提示，并配有文字，避免只依靠颜色传达信息。
[['绿色', C.green], ['黄色', C.amber], ['红色', C.red]].forEach((item, index) => {
  slide.addShape(S.ellipse, {
    x: 0.58 + index * 0.88, y: 5.9, w: 0.18, h: 0.18,
    fill: { color: item[1] }, line: { color: item[1] }
  });
  slide.addText(item[0], {
    x: 0.82 + index * 0.88, y: 5.87, w: 0.5, h: 0.22,
    fontSize: 9, color: C.white, margin: 0
  });
});

// 右侧为正式封面信息，不再出现“团队内部启动会”或“风格样稿”。
slide.addText('银行 AI 智能体\n全流程规划', {
  x: 4.75, y: 1.62, w: 7.4, h: 1.22,
  fontSize: 31, bold: true, color: C.ink, margin: 0
});
slide.addText('从自然语言交互，到可审计、可验证、可恢复的银行业务执行。', {
  x: 4.78, y: 3.18, w: 6.9, h: 0.5,
  fontSize: 14, color: C.muted, margin: 0
});
slide.addShape(S.line, {
  x: 4.78, y: 4.18, w: 7.12, h: 0,
  line: { color: C.line, width: 1 }
});
slide.addText('产品范围', {
  x: 4.78, y: 4.5, w: 1.2, h: 0.25,
  fontSize: 9, bold: true, color: C.muted, margin: 0
});
slide.addText('转账 · 账单 · 理财 · 卡片 · 订阅 · 跨场景联动', {
  x: 4.78, y: 4.87, w: 7.4, h: 0.36,
  fontSize: 13, color: C.ink, margin: 0
});
slide.addText('V0.1  |  项目启动前规划', {
  x: 4.78, y: 6.45, w: 3.5, h: 0.22,
  fontSize: 9, color: C.muted, margin: 0
});

// 第二页：Agent 开发全过程分层
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('DEVELOPMENT LAYERS', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, charSpacing: 0, margin: 0
  });
  slide.addText('Agent 开发不是只接一个大模型，而是完整的分层系统', {
    x: 0.62, y: 0.72, w: 11.9, h: 0.48,
    fontSize: 24, bold: true, color: C.ink, margin: 0
  });
  slide.addText('主链路负责处理用户请求；模拟数据、审计与恢复作为基础能力支撑整个系统。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左侧：模拟银行数据在项目开发期先生成、验证，再写入业务数据库。
  slide.addShape(S.roundRect, {
    x: 0.62, y: 1.9, w: 2.35, h: 4.63,
    rectRadius: 0.05,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.2 }
  });
  slide.addShape(S.rect, {
    x: 0.62, y: 1.9, w: 2.35, h: 0.1,
    fill: { color: C.teal }, line: { color: C.teal }
  });
  slide.addText('模拟数据准备', {
    x: 0.86, y: 2.2, w: 1.7, h: 0.3,
    fontSize: 15, bold: true, color: C.ink, margin: 0
  });
  slide.addText('系统启动前完成', {
    x: 0.86, y: 2.56, w: 1.4, h: 0.2,
    fontSize: 9, color: C.teal, bold: true, margin: 0
  });
  const dataSteps = [
    ['01', '设计典型用户画像'],
    ['02', '生成账户、账本与交易'],
    ['03', '生成订阅、持仓与风险测评'],
    ['04', '注入可复现的异常场景'],
    ['05', '执行数据一致性验证']
  ];
  dataSteps.forEach((item, index) => {
    const y = 3.02 + index * 0.57;
    slide.addShape(S.ellipse, {
      x: 0.86, y, w: 0.32, h: 0.32,
      fill: { color: index === 4 ? C.teal : 'E5F2F0' },
      line: { color: C.teal, width: 1 }
    });
    slide.addText(item[0], {
      x: 0.86, y: y + 0.065, w: 0.32, h: 0.14,
      fontSize: 7.5, bold: true,
      color: index === 4 ? C.white : C.teal,
      align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 1.26, y: y + 0.015, w: 1.52, h: 0.27,
      fontSize: 9.0, color: C.ink, margin: 0, fit: 'shrink'
    });
    if (index < dataSteps.length - 1) {
      slide.addShape(S.line, {
        x: 1.02, y: y + 0.33, w: 0, h: 0.24,
        line: { color: 'AFC8C4', width: 1 }
      });
    }
  });
  slide.addShape(S.roundRect, {
    x: 0.85, y: 5.98, w: 1.83, h: 0.34,
    rectRadius: 0.04,
    fill: { color: 'E5F2F0' }, line: { color: 'B9D7D3' }
  });
  slide.addText('固定随机种子 · 可重复演示', {
    x: 0.91, y: 6.07, w: 1.71, h: 0.15,
    fontSize: 8, bold: true, color: C.teal, align: 'center', margin: 0
  });

  // 中部：从交互到数据的六层主链路。
  const layers = [
    ['1', '用户交互层', 'React / APP / IM / 语音 · 业务卡片与确认页面', 'FFFFFF', '6C9FC2'],
    ['2', 'API 接入层', 'FastAPI · Session · 请求标准化 · 限流与 trace_id', 'E9F1F7', '4F7FA3'],
    ['3', 'Agent 编排层', 'LLM 意图理解 · LangGraph 计划 · 澄清 · Checkpoint', 'E9F1F7', C.navy2],
    ['4', '安全决策层', '操作白名单 · 绿色 / 黄色 / 红色 · 确认与强认证', 'FBF1D8', C.amber],
    ['5', '银行业务层', '账户 · 转账 · 账单 · 理财 · 卡片 · 订阅 · 任务', 'E5F2F0', C.teal],
    ['6', '数据存储层', '模拟账本与业务事实 · PostgreSQL · Checkpoint 存储', 'E8F3EC', C.green]
  ];
  layers.forEach((layer, index) => {
    const y = 1.9 + index * 0.76;
    slide.addShape(S.roundRect, {
      x: 3.42, y, w: 7.25, h: 0.61,
      rectRadius: 0.035,
      fill: { color: layer[3] }, line: { color: layer[4], width: 1.1 }
    });
    slide.addShape(S.ellipse, {
      x: 3.62, y: y + 0.145, w: 0.31, h: 0.31,
      fill: { color: layer[4] }, line: { color: layer[4] }
    });
    slide.addText(layer[0], {
      x: 3.62, y: y + 0.205, w: 0.31, h: 0.13,
      fontSize: 7.5, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(layer[1], {
      x: 4.08, y: y + 0.12, w: 1.5, h: 0.25,
      fontSize: 12.5, bold: true, color: C.ink, margin: 0
    });
    slide.addText(layer[2], {
      x: 5.58, y: y + 0.15, w: 4.75, h: 0.22,
      fontSize: 9.2, color: C.muted, margin: 0, fit: 'shrink'
    });
    if (index < layers.length - 1) {
      slide.addShape(S.line, {
        x: 7.05, y: y + 0.62, w: 0, h: 0.14,
        line: { color: '8A99A5', width: 1.2, endArrowType: 'triangle' }
      });
    }
  });

  // 模拟数据只写入数据层，不由 LLM 临时编造。
  slide.addShape(S.line, {
    x: 2.97, y: 5.99, w: 0.43, h: 0,
    line: { color: C.teal, width: 1.8, endArrowType: 'triangle' }
  });
  slide.addText('写入', {
    x: 2.98, y: 5.7, w: 0.38, h: 0.18,
    fontSize: 8, bold: true, color: C.teal, align: 'center', margin: 0
  });

  // 右侧：横跨所有层的治理能力。
  slide.addShape(S.roundRect, {
    x: 11.05, y: 1.9, w: 1.65, h: 4.63,
    rectRadius: 0.05,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1.2 }
  });
  slide.addText('全流程治理', {
    x: 11.28, y: 2.2, w: 1.18, h: 0.3,
    fontSize: 14, bold: true, color: '7657A6', align: 'center', margin: 0
  });
  const governance = ['审计日志', '运行监控', '异常熔断', '人工接管', '证据追踪'];
  governance.forEach((item, index) => {
    const y = 2.93 + index * 0.59;
    slide.addShape(S.roundRect, {
      x: 11.32, y, w: 1.12, h: 0.36,
      rectRadius: 0.04,
      fill: { color: index === 2 ? 'F9E7E5' : 'FFFFFF' },
      line: { color: index === 2 ? C.red : 'CDBDDE', width: 0.9 }
    });
    slide.addText(item, {
      x: 11.38, y: y + 0.09, w: 1.0, h: 0.16,
      fontSize: 8.8, bold: true,
      color: index === 2 ? C.red : '7657A6', align: 'center', margin: 0
    });
  });
  slide.addText('贯穿每一层', {
    x: 11.3, y: 6.02, w: 1.15, h: 0.2,
    fontSize: 8.5, bold: true, color: '7657A6', align: 'center', margin: 0
  });

  // 页面结论帮助团队记住模拟数据与 Agent 的边界。
  slide.addShape(S.roundRect, {
    x: 3.42, y: 6.62, w: 9.28, h: 0.38,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('关键边界：模拟数据生成底层业务事实；Agent 只能通过受控业务工具读取和操作这些事实。', {
    x: 3.65, y: 6.72, w: 8.8, h: 0.17,
    fontSize: 9.4, bold: true, color: C.navy, margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('02', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第三页：用户交互层与前端工作台效果
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('USER EXPERIENCE', {
    x: 0.62, y: 0.42, w: 3.0, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('用户交互层：对话是入口，业务卡片完成操作', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 24, bold: true, color: C.ink, margin: 0
  });
  slide.addText('同一个工作台承载自然语言输入、结构化结果、风险授权与执行过程可视化。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 主视觉使用已生成的前端工作台预览图。
  slide.addShape(S.roundRect, {
    x: 0.62, y: 1.74, w: 9.08, h: 5.11,
    rectRadius: 0.045,
    fill: { color: C.white }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addImage({
    path: '银行Agent前端工作台预览.png',
    x: 0.68, y: 1.80, w: 8.96, h: 5.04
  });

  // 右侧提炼交互原则，说明界面为何这样设计。
  slide.addText('交互重点', {
    x: 10.05, y: 1.83, w: 1.4, h: 0.3,
    fontSize: 15, bold: true, color: C.ink, margin: 0
  });
  const principles = [
    ['01', '对话统一入口', '文本、语音和渠道消息统一转换为同一种 Agent 请求。', C.navy2, 'E9F1F7'],
    ['02', '业务卡片承载动作', '图表、产品比较、确认和认证使用结构化组件呈现。', C.teal, 'E5F2F0'],
    ['03', '过程透明可追踪', '展示计划进度、风险等级和执行状态，避免黑盒体验。', C.purple, 'EFE9F6']
  ];
  principles.forEach((item, index) => {
    const y = 2.34 + index * 1.19;
    slide.addShape(S.roundRect, {
      x: 10.04, y, w: 2.67, h: 0.98,
      rectRadius: 0.04,
      fill: { color: item[4] }, line: { color: item[3], width: 1 }
    });
    slide.addShape(S.ellipse, {
      x: 10.25, y: y + 0.18, w: 0.34, h: 0.34,
      fill: { color: item[3] }, line: { color: item[3] }
    });
    slide.addText(item[0], {
      x: 10.25, y: y + 0.26, w: 0.34, h: 0.12,
      fontSize: 7.2, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 10.73, y: y + 0.16, w: 1.65, h: 0.24,
      fontSize: 11.5, bold: true, color: C.ink, margin: 0
    });
    slide.addText(item[2], {
      x: 10.25, y: y + 0.58, w: 2.18, h: 0.27,
      fontSize: 8.6, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 10.04, y: 6.02, w: 2.67, h: 0.72,
    rectRadius: 0.04,
    fill: { color: C.white }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('前端不直接调用模型或银行数据库', {
    x: 10.28, y: 6.2, w: 2.18, h: 0.2,
    fontSize: 9.3, bold: true, color: C.navy, align: 'center', margin: 0
  });
  slide.addText('所有请求统一进入 FastAPI 安全入口', {
    x: 10.28, y: 6.45, w: 2.18, h: 0.16,
    fontSize: 8, color: C.muted, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('03', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第四页：前端工程搭建与登录会话
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('FRONTEND FOUNDATION', {
    x: 0.62, y: 0.42, w: 3.1, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('前端搭建：登录建立可信会话，工作台承载业务交互', {
    x: 0.62, y: 0.72, w: 11.9, h: 0.48,
    fontSize: 24, bold: true, color: C.ink, margin: 0
  });
  slide.addText('前端负责交互、路由和状态展示；身份验证、用户归属和操作授权始终由服务端完成。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左侧：React 工程从应用壳到 API 客户端的四层结构。
  slide.addText('React 工程分层', {
    x: 0.68, y: 1.76, w: 2.0, h: 0.3,
    fontSize: 15, bold: true, color: C.ink, margin: 0
  });
  slide.addText('React + TypeScript + Vite', {
    x: 3.78, y: 1.8, w: 2.1, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, align: 'right', margin: 0
  });
  const frontendLayers = [
    ['01', '应用与路由', 'App Shell · React Router · ProtectedRoute', 'E9F1F7', C.navy2],
    ['02', '业务组件', '对话 · 图表 · 转账确认 · 强认证 · DAG', 'FFFFFF', '6C9FC2'],
    ['03', '状态与校验', 'TanStack Query · AuthContext · Zod', 'E5F2F0', C.teal],
    ['04', '通信客户端', 'REST · SSE 流式事件 · 统一错误处理', 'FFFFFF', C.green]
  ];
  frontendLayers.forEach((item, index) => {
    const y = 2.17 + index * 0.79;
    slide.addShape(S.roundRect, {
      x: 0.68, y, w: 5.2, h: 0.63,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[4], width: 1.05 }
    });
    slide.addShape(S.rect, {
      x: 0.68, y, w: 0.07, h: 0.63,
      fill: { color: item[4] }, line: { color: item[4] }
    });
    slide.addText(item[0], {
      x: 0.94, y: y + 0.19, w: 0.36, h: 0.16,
      fontSize: 8, bold: true, color: item[4], margin: 0
    });
    slide.addText(item[1], {
      x: 1.42, y: y + 0.12, w: 1.25, h: 0.24,
      fontSize: 12, bold: true, color: C.ink, margin: 0
    });
    slide.addText(item[2], {
      x: 2.7, y: y + 0.16, w: 2.82, h: 0.2,
      fontSize: 8.8, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.68, y: 5.53, w: 5.2, h: 1.12,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('建议目录', {
    x: 0.93, y: 5.76, w: 0.72, h: 0.2,
    fontSize: 9.5, bold: true, color: C.ink, margin: 0
  });
  slide.addText('app/  routes/  features/auth/  features/chat/', {
    x: 1.76, y: 5.72, w: 3.75, h: 0.22,
    fontFace: 'Consolas', fontSize: 8.7, color: C.navy, margin: 0
  });
  slide.addText('components/business-cards/  lib/api/', {
    x: 1.76, y: 6.08, w: 3.75, h: 0.22,
    fontFace: 'Consolas', fontSize: 8.7, color: C.navy, margin: 0
  });
  slide.addText('按业务能力组织代码，登录与会话作为共享基础模块。', {
    x: 0.93, y: 6.31, w: 4.58, h: 0.16,
    fontSize: 8.2, color: C.muted, margin: 0
  });

  // 右侧：服务端 Session 登录流程。
  slide.addText('登录与可信会话流程', {
    x: 6.35, y: 1.76, w: 2.3, h: 0.3,
    fontSize: 15, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 6.35, y: 2.17, w: 6.32, h: 2.82,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  const loginSteps = [
    ['1', '/login', '输入账号与密码', C.navy2],
    ['2', 'POST /auth/login', 'FastAPI 校验凭据', C.teal],
    ['3', 'Set-Cookie', '签发 HttpOnly Session', C.amber],
    ['4', 'GET /auth/me', '恢复用户与账户上下文', C.purple],
    ['5', '/app', '进入受保护工作台', C.green]
  ];
  loginSteps.forEach((item, index) => {
    const x = 6.62 + index * 1.19;
    slide.addShape(S.ellipse, {
      x: x + 0.3, y: 2.47, w: 0.38, h: 0.38,
      fill: { color: item[3] }, line: { color: item[3] }
    });
    slide.addText(item[0], {
      x: x + 0.3, y: 2.56, w: 0.38, h: 0.13,
      fontSize: 7.5, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x, y: 3.03, w: 0.98, h: 0.25,
      fontFace: index === 0 || index === 4 ? 'Microsoft YaHei' : 'Consolas',
      fontSize: 8.2, bold: true, color: C.ink, align: 'center', margin: 0, fit: 'shrink'
    });
    slide.addText(item[2], {
      x: x - 0.04, y: 3.42, w: 1.06, h: 0.42,
      fontSize: 8, color: C.muted, align: 'center', margin: 0, fit: 'shrink'
    });
    if (index < loginSteps.length - 1) {
      slide.addShape(S.line, {
        x: x + 0.72, y: 2.66, w: 0.47, h: 0,
        line: { color: '9AA8B3', width: 1.2, endArrowType: 'triangle' }
      });
    }
  });
  slide.addShape(S.roundRect, {
    x: 6.64, y: 4.21, w: 5.71, h: 0.48,
    rectRadius: 0.035,
    fill: { color: 'E9F1F7' }, line: { color: 'BFD2E1', width: 1 }
  });
  slide.addText('ProtectedRoute 未取得有效 Session 时，统一跳转登录页；Agent 流程不会启动。', {
    x: 6.88, y: 4.34, w: 5.24, h: 0.18,
    fontSize: 8.7, bold: true, color: C.navy, align: 'center', margin: 0
  });

  // 登录安全边界。
  slide.addText('登录安全边界', {
    x: 6.35, y: 5.32, w: 1.8, h: 0.3,
    fontSize: 13.5, bold: true, color: C.ink, margin: 0
  });
  const rules = [
    ['不存 Token', '访问凭证放在 HttpOnly、Secure、SameSite Cookie 中。', C.red, 'F9E7E5'],
    ['不信前端身份', 'user_id 与 account_id 由服务端 Session 注入。', C.amber, 'FBF1D8'],
    ['强认证分离', '登录态不等于支付授权；红色操作再次认证。', C.purple, 'EFE9F6']
  ];
  rules.forEach((item, index) => {
    const x = 6.35 + index * 2.13;
    slide.addShape(S.roundRect, {
      x, y: 5.73, w: 1.92, h: 0.92,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: x + 0.16, y: 5.91, w: 1.6, h: 0.21,
      fontSize: 9.5, bold: true, color: item[2], align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: x + 0.15, y: 6.2, w: 1.62, h: 0.27,
      fontSize: 7.7, color: C.muted, align: 'center', margin: 0, fit: 'shrink'
    });
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('04', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 旧版前端代码页不再输出，保留结构仅用于后续内容追溯。
if (false) {
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('FRONTEND CODE WALKTHROUGH', {
    x: 0.62, y: 0.42, w: 3.8, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('前端关键代码：登录成功后，才挂载 Agent 工作台', {
    x: 0.62, y: 0.72, w: 11.9, h: 0.48,
    fontSize: 24, bold: true, color: C.ink, margin: 0
  });
  slide.addText('以下代码只表达核心职责与数据流；正式实现再拆分组件、异常状态和测试。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  const panels = [
    {
      x: 0.62, w: 3.92, color: C.teal, file: 'api.ts', step: '01  建立服务端会话',
      code: [
        'export async function login(input) {',
        '  const res = await fetch(',
        '    "/api/auth/login", {',
        '      method: "POST",',
        '      credentials: "include",',
        '      headers: {',
        '        "Content-Type": "application/json"',
        '      },',
        '      body: JSON.stringify(input)',
        '    }',
        '  );',
        '',
        '  if (!res.ok) throw Error("登录失败");',
        '  return res.json();',
        '}'
      ].join('\n')
    },
    {
      x: 4.72, w: 3.92, color: C.navy2, file: 'App.tsx', step: '02  保护工作台路由',
      code: [
        'function ProtectedRoute() {',
        '  const { user, loading } = useAuth();',
        '',
        '  if (loading) return <Loading />;',
        '  return user',
        '    ? <Outlet />',
        '    : <Navigate to="/login" replace />;',
        '}',
        '',
        '<Routes>',
        '  <Route path="/login"',
        '    element={<LoginPage />} />',
        '  <Route element={<ProtectedRoute />}>',
        '    <Route path="/app"',
        '      element={<AgentWorkbench />} />',
        '  </Route>',
        '</Routes>'
      ].join('\n')
    },
    {
      x: 8.82, w: 3.89, color: C.purple, file: 'AgentWorkbench.tsx', step: '03  渲染结构化事件',
      code: [
        'function EventView({ event }) {',
        '  switch (event.type) {',
        '    case "bill.summary":',
        '      return <BillCard data={event} />;',
        '',
        '    case "confirmation.required":',
        '      return <TransferConfirm',
        '        challenge={event} />;',
        '',
        '    case "authentication.required":',
        '      return <StrongAuth data={event} />;',
        '',
        '    default:',
        '      return <ChatMessage data={event} />;',
        '  }',
        '}'
      ].join('\n')
    }
  ];

  panels.forEach((panel) => {
    slide.addShape(S.roundRect, {
      x: panel.x, y: 1.76, w: panel.w, h: 4.74,
      rectRadius: 0.04,
      fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
    });
    slide.addShape(S.rect, {
      x: panel.x, y: 1.76, w: panel.w, h: 0.1,
      fill: { color: panel.color }, line: { color: panel.color }
    });
    slide.addText(panel.step, {
      x: panel.x + 0.22, y: 2.03, w: panel.w - 1.82, h: 0.24,
      fontSize: 10.5, bold: true, color: C.ink, margin: 0
    });
    slide.addShape(S.roundRect, {
      x: panel.x + panel.w - 1.54, y: 2.02, w: 1.32, h: 0.26,
      rectRadius: 0.03,
      fill: { color: panel.color }, line: { color: panel.color }
    });
    slide.addText(panel.file, {
      x: panel.x + panel.w - 1.54, y: 2.085, w: 1.32, h: 0.12,
      fontFace: 'Consolas', fontSize: 7.5, bold: true,
      color: C.white, align: 'center', margin: 0
    });
    slide.addShape(S.roundRect, {
      x: panel.x + 0.19, y: 2.48, w: panel.w - 0.38, h: 3.73,
      rectRadius: 0.03,
      fill: { color: 'F6F8FA' }, line: { color: 'E1E6EA', width: 0.8 }
    });
    slide.addText(panel.code, {
      x: panel.x + 0.36, y: 2.68, w: panel.w - 0.72, h: 3.34,
      fontFace: 'Consolas', fontSize: 7.8, color: C.ink,
      margin: 0, breakLine: false, valign: 'top', fit: 'shrink'
    });
  });

  // 三条边界把代码片段与银行安全设计关联起来。
  const rules = [
    ['Cookie 自动携带', 'credentials: include'],
    ['前端不提交身份', 'user_id 来自 Session'],
    ['界面由事件驱动', 'event.type → 业务卡片']
  ];
  rules.forEach((item, index) => {
    const x = 0.73 + index * 4.05;
    slide.addShape(S.ellipse, {
      x, y: 6.73, w: 0.18, h: 0.18,
      fill: { color: index === 0 ? C.teal : index === 1 ? C.amber : C.purple },
      line: { color: index === 0 ? C.teal : index === 1 ? C.amber : C.purple }
    });
    slide.addText(item[0], {
      x: x + 0.29, y: 6.67, w: 1.25, h: 0.2,
      fontSize: 8.5, bold: true, color: C.ink, margin: 0
    });
    slide.addText(item[1], {
      x: x + 1.5, y: 6.67, w: 2.0, h: 0.2,
      fontFace: 'Consolas', fontSize: 7.8, color: C.muted, margin: 0
    });
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('05', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第五页：用户输入如何传输到后端
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('REQUEST CONTRACT', {
    x: 0.62, y: 0.42, w: 3.1, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('前端发出的不是一段裸文本，而是一份结构化请求', {
    x: 0.62, y: 0.72, w: 11.9, h: 0.48,
    fontSize: 24, bold: true, color: C.ink, margin: 0
  });
  slide.addText('用户输入作为 message 发送；会话、渠道与客户端请求标识帮助后端恢复流程、去重和追踪。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左侧：用户在工作台中的输入状态。
  slide.addText('1  用户输入', {
    x: 0.68, y: 1.77, w: 1.5, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 0.68, y: 2.17, w: 2.55, h: 2.7,
    rectRadius: 0.05,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 0.68, y: 2.17, w: 2.55, h: 0.48,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('智银 Agent', {
    x: 0.94, y: 2.32, w: 1.1, h: 0.18,
    fontSize: 10, bold: true, color: C.white, margin: 0
  });
  slide.addText('请输入你想办理的业务', {
    x: 0.94, y: 2.95, w: 1.85, h: 0.23,
    fontSize: 9.5, color: C.muted, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 0.92, y: 3.37, w: 2.07, h: 0.83,
    rectRadius: 0.04,
    fill: { color: 'F6F8FA' }, line: { color: C.line, width: 1 }
  });
  slide.addText('给张伟转 300 元，\n备注聚餐 AA。', {
    x: 1.1, y: 3.56, w: 1.65, h: 0.42,
    fontSize: 11, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 2.14, y: 4.38, w: 0.84, h: 0.3,
    rectRadius: 0.03,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('发送', {
    x: 2.14, y: 4.46, w: 0.84, h: 0.13,
    fontSize: 8.5, bold: true, color: C.white, align: 'center', margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 0.68, y: 5.18, w: 2.55, h: 1.3,
    rectRadius: 0.04,
    fill: { color: 'E9F1F7' }, line: { color: 'BFD2E1', width: 1 }
  });
  slide.addText('此时前端只知道', {
    x: 0.91, y: 5.42, w: 1.2, h: 0.2,
    fontSize: 9, bold: true, color: C.navy, margin: 0
  });
  slide.addText('• 用户输入的文字\n• 当前 thread_id\n• 当前页面与渠道信息', {
    x: 0.91, y: 5.76, w: 1.95, h: 0.5,
    fontSize: 8.5, color: C.muted, margin: 0
  });

  // 中间：发送给 FastAPI 的请求体。
  slide.addText('2  组装请求体', {
    x: 3.65, y: 1.77, w: 1.75, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 3.65, y: 2.17, w: 4.76, h: 4.31,
    rectRadius: 0.045,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 3.65, y: 2.17, w: 4.76, h: 0.5,
    fill: { color: C.navy2 }, line: { color: C.navy2 }
  });
  slide.addText('POST  /api/agent/messages', {
    x: 3.9, y: 2.32, w: 2.9, h: 0.18,
    fontFace: 'Consolas', fontSize: 9.5, bold: true, color: C.white, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 6.92, y: 2.29, w: 1.15, h: 0.25,
    rectRadius: 0.03,
    fill: { color: C.teal }, line: { color: C.teal }
  });
  slide.addText('application/json', {
    x: 6.92, y: 2.36, w: 1.15, h: 0.11,
    fontFace: 'Consolas', fontSize: 6.8, bold: true, color: C.white, align: 'center', margin: 0
  });
  const payload = [
    '{',
    '  "message": "给张伟转 300 元，备注聚餐 AA",',
    '  "thread_id": "thread-20261008-001",',
    '  "client_request_id": "web-7f3c92",',
    '  "channel": "web",',
    '  "locale": "zh-CN",',
    '  "timezone": "Asia/Shanghai"',
    '}'
  ].join('\n');
  slide.addShape(S.roundRect, {
    x: 3.9, y: 2.94, w: 4.26, h: 2.42,
    rectRadius: 0.03,
    fill: { color: 'F6F8FA' }, line: { color: 'E1E6EA', width: 0.8 }
  });
  slide.addText(payload, {
    x: 4.1, y: 3.16, w: 3.87, h: 1.95,
    fontFace: 'Consolas', fontSize: 8.2, color: C.ink,
    margin: 0, breakLine: false, valign: 'top', fit: 'shrink'
  });
  slide.addText('字段用途', {
    x: 3.93, y: 5.63, w: 0.72, h: 0.18,
    fontSize: 8.7, bold: true, color: C.ink, margin: 0
  });
  slide.addText('message：业务原文     thread_id：恢复同一会话     client_request_id：防重复提交', {
    x: 4.72, y: 5.61, w: 3.3, h: 0.23,
    fontSize: 7.7, color: C.muted, margin: 0, fit: 'shrink'
  });
  slide.addText('channel / locale / timezone：用于渠道适配、语言与时间解析，不用于业务授权。', {
    x: 3.93, y: 6.03, w: 4.05, h: 0.2,
    fontSize: 7.8, color: C.muted, margin: 0
  });

  // 右侧：传输方法和服务端可信字段。
  slide.addText('3  传输与返回', {
    x: 8.83, y: 1.77, w: 1.8, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const transport = [
    ['HTTP POST', '提交一次用户输入和上下文', C.navy2, 'E9F1F7'],
    ['Session Cookie', 'credentials: include 自动携带', C.teal, 'E5F2F0'],
    ['CSRF Header', 'Cookie 登录下防止跨站伪造', C.amber, 'FBF1D8'],
    ['SSE', '流式返回节点进度与业务事件', C.purple, 'EFE9F6']
  ];
  transport.forEach((item, index) => {
    const y = 2.17 + index * 0.79;
    slide.addShape(S.roundRect, {
      x: 8.83, y, w: 3.84, h: 0.62,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 9.06, y: y + 0.13, w: 1.15, h: 0.21,
      fontFace: item[0] === 'Session Cookie' ? 'Microsoft YaHei' : 'Consolas',
      fontSize: 9, bold: true, color: item[2], margin: 0
    });
    slide.addText(item[1], {
      x: 10.24, y: y + 0.15, w: 2.12, h: 0.19,
      fontSize: 8.3, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 8.83, y: 5.49, w: 3.84, h: 0.99,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('FastAPI 在服务端补充可信字段', {
    x: 9.07, y: 5.7, w: 2.55, h: 0.2,
    fontSize: 9.5, bold: true, color: C.ink, margin: 0
  });
  slide.addText('user_id · account_id  ← Session\nrequest_id · trace_id · received_at  ← 服务端生成', {
    x: 9.07, y: 6.04, w: 3.2, h: 0.3,
    fontFace: 'Consolas', fontSize: 7.8, color: C.navy, margin: 0
  });

  // 信任边界：明确哪些字段绝不能让前端自行声明。
  slide.addShape(S.roundRect, {
    x: 0.68, y: 6.7, w: 11.99, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('前端不发送或不能决定：user_id · risk_level · authorized · balance · operation_result', {
    x: 0.93, y: 6.79, w: 11.5, h: 0.15,
    fontFace: 'Consolas', fontSize: 8.4, bold: true, color: C.red, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('05', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第六页：API 接入层
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('API ACCESS LAYER', {
    x: 0.62, y: 0.42, w: 3.1, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('API 接入层：把多渠道请求转换为可信、可追踪的 Agent 输入', {
    x: 0.62, y: 0.72, w: 12.0, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('FastAPI 是前端与 Agent 之间唯一入口：先建立可信上下文，再允许 LangGraph 开始运行。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 上半部分：从渠道进入 LangGraph 的请求处理流水线。
  slide.addText('请求进入流水线', {
    x: 0.68, y: 1.74, w: 1.7, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const stages = [
    ['多渠道输入', 'Web · IM · 语音', C.navy2, 'E9F1F7'],
    ['身份恢复', 'Session → user_id', C.teal, 'E5F2F0'],
    ['请求校验', 'Pydantic Schema', '4F7FA3', 'E9F1F7'],
    ['入口防护', 'CSRF · 限流 · 异常', C.amber, 'FBF1D8'],
    ['标准化', '渠道 → AgentRequest', C.purple, 'EFE9F6'],
    ['Agent 调用', 'LangGraph + SSE', C.green, 'E8F3EC']
  ];
  stages.forEach((item, index) => {
    const x = 0.68 + index * 2.05;
    slide.addShape(S.roundRect, {
      x, y: 2.17, w: 1.73, h: 1.12,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1.05 }
    });
    slide.addShape(S.ellipse, {
      x: x + 0.66, y: 2.37, w: 0.4, h: 0.4,
      fill: { color: item[2] }, line: { color: item[2] }
    });
    slide.addText(String(index + 1), {
      x: x + 0.66, y: 2.47, w: 0.4, h: 0.13,
      fontSize: 7.5, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[0], {
      x: x + 0.12, y: 2.83, w: 1.49, h: 0.2,
      fontSize: 9.5, bold: true, color: C.ink, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: x + 0.1, y: 3.08, w: 1.53, h: 0.14,
      fontFace: item[1].includes('Pydantic') || item[1].includes('LangGraph') ? 'Consolas' : 'Microsoft YaHei',
      fontSize: 7.4, color: C.muted, align: 'center', margin: 0, fit: 'shrink'
    });
    if (index < stages.length - 1) {
      slide.addShape(S.line, {
        x: x + 1.75, y: 2.73, w: 0.28, h: 0,
        line: { color: '8E9BA6', width: 1.1, endArrowType: 'triangle' }
      });
    }
  });

  // 左下：标准化后的 AgentRequest，标注字段来源。
  slide.addText('统一 AgentRequest', {
    x: 0.68, y: 3.71, w: 1.9, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 0.68, y: 4.12, w: 5.43, h: 2.47,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  const requestLines = [
    ['user_id', '"user-001"', 'Session 注入', C.green],
    ['account_id', '"account-001"', 'Session 注入', C.green],
    ['message', '"给张伟转 300 元"', '用户输入', C.navy2],
    ['channel', '"web"', '渠道标准化', C.purple],
    ['request_id', '"req-..."', '服务端生成', C.teal],
    ['trace_id', '"trace-..."', '服务端生成', C.teal]
  ];
  requestLines.forEach((item, index) => {
    const y = 4.37 + index * 0.32;
    slide.addText(item[0], {
      x: 0.94, y, w: 0.98, h: 0.16,
      fontFace: 'Consolas', fontSize: 8.3, bold: true, color: C.ink, margin: 0
    });
    slide.addText(':', {
      x: 1.9, y, w: 0.12, h: 0.16,
      fontFace: 'Consolas', fontSize: 8.3, color: C.muted, margin: 0
    });
    slide.addText(item[1], {
      x: 2.06, y, w: 1.7, h: 0.16,
      fontFace: 'Consolas', fontSize: 8.1, color: item[3], margin: 0, fit: 'shrink'
    });
    slide.addShape(S.roundRect, {
      x: 4.23, y: y - 0.025, w: 1.35, h: 0.22,
      rectRadius: 0.03,
      fill: { color: index < 2 ? 'E8F3EC' : index === 2 ? 'E9F1F7' : 'EFE9F6' },
      line: { color: item[3], width: 0.8 }
    });
    slide.addText(item[2], {
      x: 4.23, y: y + 0.035, w: 1.35, h: 0.1,
      fontSize: 7, bold: true, color: item[3], align: 'center', margin: 0
    });
  });
  slide.addText('只有绿色标记的身份字段可作为业务授权依据；message 始终是不可信输入。', {
    x: 0.94, y: 6.35, w: 4.85, h: 0.16,
    fontSize: 7.9, color: C.muted, margin: 0
  });

  // 右下：MVP 接口清单和职责边界。
  slide.addText('MVP 接口与职责', {
    x: 6.47, y: 3.71, w: 1.9, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 6.47, y: 4.12, w: 6.2, h: 2.47,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  const endpoints = [
    ['POST', '/auth/login', '建立登录 Session'],
    ['GET', '/auth/me', '恢复当前用户上下文'],
    ['POST', '/agent/messages', '提交自然语言请求'],
    ['GET', '/agent/runs/{id}/events', 'SSE 返回流程事件'],
    ['POST', '/agent/runs/{id}/resume', '恢复确认或认证中断'],
    ['GET', '/operations/{id}', '查询最终业务状态']
  ];
  endpoints.forEach((item, index) => {
    const col = index < 3 ? 0 : 1;
    const row = index % 3;
    const x = 6.75 + col * 2.93;
    const y = 4.4 + row * 0.52;
    slide.addShape(S.roundRect, {
      x, y, w: 0.52, h: 0.23,
      rectRadius: 0.025,
      fill: { color: item[0] === 'POST' ? C.teal : C.navy2 },
      line: { color: item[0] === 'POST' ? C.teal : C.navy2 }
    });
    slide.addText(item[0], {
      x, y: y + 0.062, w: 0.52, h: 0.1,
      fontFace: 'Consolas', fontSize: 6.5, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: x + 0.64, y: y + 0.02, w: 2.05, h: 0.15,
      fontFace: 'Consolas', fontSize: 7.4, bold: true, color: C.ink, margin: 0, fit: 'shrink'
    });
    slide.addText(item[2], {
      x: x + 0.64, y: y + 0.23, w: 2.05, h: 0.14,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
  });
  slide.addShape(S.roundRect, {
    x: 6.75, y: 6.05, w: 5.61, h: 0.34,
    rectRadius: 0.03,
    fill: { color: 'FBF1D8' }, line: { color: 'E8C76F', width: 1 }
  });
  slide.addText('API 接入层不理解业务意图、不决定风险等级，也不直接执行转账。', {
    x: 6.96, y: 6.14, w: 5.18, h: 0.14,
    fontSize: 8.2, bold: true, color: '8A6212', align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('06', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 旧版完整流程图页不再输出；完整图改为独立 SVG，通过新版第七页超链接打开。
if (false) {
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('AGENT ORCHESTRATION', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('Agent 编排层：节点控制流程，State 传递结构化上下文', {
    x: 0.62, y: 0.72, w: 11.9, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('第一版 LangGraph 覆盖信息补全、计划校验、风险分流、中断授权、可信执行和统一回复。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  const node = (x, y, w, h, label, color, fill = 'FFFFFF', fontSize = 7.8) => {
    slide.addShape(S.roundRect, {
      x, y, w, h, rectRadius: 0.03,
      fill: { color: fill }, line: { color, width: 1 }
    });
    slide.addText(label, {
      x: x + 0.07, y: y + 0.06, w: w - 0.14, h: h - 0.12,
      fontFace: 'Consolas', fontSize, bold: true, color,
      align: 'center', valign: 'mid', margin: 0, fit: 'shrink'
    });
  };
  const arrow = (x, y, w, h, color = '8E9BA6', dash = 'solid') => {
    slide.addShape(S.line, {
      x, y, w, h,
      line: { color, width: 1.05, dash, endArrowType: 'triangle' }
    });
  };
  const branchLabel = (text, x, y, w, color) => {
    slide.addText(text, {
      x, y, w, h: 0.13,
      fontSize: 6.6, bold: true, color, align: 'center', margin: 0
    });
  };

  // 左侧主流程：节点名称与教学代码中的 add_node 保持一致。
  slide.addText('LangGraph 节点与条件边', {
    x: 0.58, y: 1.64, w: 2.3, h: 0.25,
    fontSize: 13, bold: true, color: C.ink, margin: 0
  });
  node(0.58, 2.02, 0.62, 0.42, 'START', C.navy, 'E9F1F7', 7.2);
  node(1.43, 2.02, 1.13, 0.42, 'load_context', C.navy2, 'E9F1F7');
  node(2.82, 2.02, 1.35, 0.42, 'understand_intent', C.purple, 'EFE9F6', 7.3);
  node(4.43, 2.02, 1.22, 0.42, 'resolve_entities', C.purple, 'EFE9F6', 7.2);
  arrow(1.2, 2.23, 0.23, 0);
  arrow(2.56, 2.23, 0.26, 0);
  arrow(4.17, 2.23, 0.26, 0);

  // 信息缺失路径与计划创建路径。
  node(2.05, 3.0, 1.48, 0.46, 'ask_clarification', C.amber, 'FBF1D8', 7.2);
  node(4.43, 3.0, 1.22, 0.46, 'create_plan', C.navy2, 'E9F1F7');
  node(5.94, 3.0, 1.22, 0.46, 'validate_plan', C.navy2, 'E9F1F7');
  node(7.46, 3.0, 1.15, 0.46, 'reject_plan', C.red, 'F9E7E5');
  arrow(5.04, 2.44, -2.25, 0.56, C.amber);
  branchLabel('信息缺失', 3.05, 2.69, 0.78, C.amber);
  arrow(5.04, 2.44, 0, 0.56, C.navy2);
  branchLabel('信息完整', 5.17, 2.69, 0.78, C.navy2);
  arrow(5.65, 3.23, 0.29, 0);
  arrow(7.16, 3.23, 0.3, 0, C.red);
  branchLabel('无效', 7.13, 3.04, 0.34, C.red);
  node(2.41, 3.73, 0.76, 0.36, 'END', C.muted, 'EEF2F5', 7.2);
  arrow(2.79, 3.46, 0, 0.27, C.amber);

  // 计划有效后进入确定性安全策略。
  node(5.94, 3.9, 1.22, 0.46, 'security_policy', C.amber, 'FBF1D8', 7.2);
  arrow(6.55, 3.46, 0, 0.44, C.amber);
  branchLabel('有效', 6.64, 3.6, 0.35, C.green);

  // 四级权限分流。
  node(0.64, 4.92, 1.18, 0.48, 'execute_query', C.green, 'E8F3EC');
  node(2.17, 4.92, 1.76, 0.48, 'interrupt_for_\nconfirmation', C.amber, 'FBF1D8', 6.9);
  node(4.28, 4.92, 1.86, 0.48, 'interrupt_for_\nauthentication', C.red, 'F9E7E5', 6.8);
  node(6.53, 4.92, 1.55, 0.48, 'reject_operation', C.red, 'F9E7E5', 7.2);
  arrow(6.55, 4.36, -5.32, 0.56, C.green);
  arrow(6.55, 4.36, -3.5, 0.56, C.amber);
  arrow(6.55, 4.36, -1.34, 0.56, C.red);
  arrow(6.55, 4.36, 0.75, 0.56, C.red);
  branchLabel('GREEN', 1.04, 4.6, 0.55, C.green);
  branchLabel('YELLOW', 2.78, 4.6, 0.62, C.amber);
  branchLabel('RED', 4.95, 4.6, 0.5, C.red);
  branchLabel('DENY', 7.12, 4.6, 0.5, C.red);

  // 中断恢复后，授权成功进入写操作，失败进入统一拒绝。
  node(3.24, 5.96, 1.58, 0.48, 'execute_operation', C.green, 'E8F3EC', 7.2);
  node(5.31, 5.96, 1.48, 0.48, 'compose_response', C.navy2, 'E9F1F7', 7.2);
  node(7.34, 5.96, 0.76, 0.48, 'END', C.muted, 'EEF2F5', 7.2);
  arrow(3.05, 5.4, 0.72, 0.56, C.green);
  arrow(5.21, 5.4, -0.87, 0.56, C.green);
  branchLabel('授权通过', 3.63, 5.64, 0.68, C.green);
  arrow(3.93, 5.16, 2.92, 0.34, C.red, 'dash');
  arrow(5.21, 5.16, 1.64, 0.34, C.red, 'dash');
  branchLabel('拒绝 / 认证失败', 5.58, 5.43, 1.08, C.red);
  arrow(1.23, 5.4, 4.08, 0.8, C.green);
  arrow(4.82, 6.2, 0.49, 0);
  arrow(6.79, 6.2, 0.55, 0);
  arrow(8.08, 5.16, -1.54, 0.8, C.red);
  arrow(8.03, 3.46, -1.49, 2.5, C.red, 'dash');

  // load_context 校验失败直接进入回复节点。
  arrow(1.99, 2.44, -0.96, 3.42, C.red, 'dash');
  arrow(1.03, 5.86, 4.28, 0.34, C.red, 'dash');
  branchLabel('上下文无效', 0.7, 4.07, 0.78, C.red);

  // 右侧：BankAgentState 的完整字段分组。
  slide.addShape(S.line, {
    x: 8.88, y: 1.67, w: 0, h: 5.13,
    line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('BankAgentState', {
    x: 9.18, y: 1.64, w: 2.0, h: 0.25,
    fontFace: 'Consolas', fontSize: 13, bold: true, color: C.ink, margin: 0
  });
  slide.addText('节点读取旧 State，只返回需要更新的字段', {
    x: 9.18, y: 1.96, w: 3.2, h: 0.18,
    fontSize: 8, color: C.muted, margin: 0
  });
  const stateGroups = [
    {
      y: 2.27, h: 1.12, title: '可信请求上下文', color: C.green, fill: 'E8F3EC',
      fields: 'user_id · account_id · request_id\nmessage · daily_transfer_total\nbalance · context_valid'
    },
    {
      y: 3.5, h: 0.98, title: '模型候选理解', color: C.purple, fill: 'EFE9F6',
      fields: 'intent · recipient_name · contact_id\namount · missing_fields'
    },
    {
      y: 4.59, h: 1.14, title: '计划与安全决策', color: C.amber, fill: 'FBF1D8',
      fields: 'plan · plan_valid · risk_level\noperation_hash · challenge_id\nauthorized'
    },
    {
      y: 5.84, h: 0.8, title: '执行与回复结果', color: C.navy2, fill: 'E9F1F7',
      fields: 'status · result · response'
    }
  ];
  stateGroups.forEach((group) => {
    slide.addShape(S.roundRect, {
      x: 9.17, y: group.y, w: 3.5, h: group.h,
      rectRadius: 0.035,
      fill: { color: group.fill }, line: { color: group.color, width: 1 }
    });
    slide.addText(group.title, {
      x: 9.4, y: group.y + 0.16, w: 1.55, h: 0.2,
      fontSize: 9.5, bold: true, color: group.color, margin: 0
    });
    slide.addText(group.fields, {
      x: 9.4, y: group.y + 0.45, w: 3.02, h: group.h - 0.54,
      fontFace: 'Consolas', fontSize: 7.4, color: C.ink,
      margin: 0, valign: 'top', fit: 'shrink'
    });
  });
  slide.addShape(S.roundRect, {
    x: 9.17, y: 6.74, w: 3.5, h: 0.3,
    rectRadius: 0.03,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 0.9 }
  });
  slide.addText('Checkpoint = State + 执行位置   |   thread_id 是配置键，不在 State 中', {
    x: 9.31, y: 6.82, w: 3.22, h: 0.12,
    fontSize: 6.7, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('07', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第七页：API 输入如何形成 State，以及 State 后续流向
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('AGENT STATE', {
    x: 0.62, y: 0.42, w: 2.8, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('Agent 编排层：上一层输入如何成为 BankAgentState', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('load_context 建立可信初始状态；后续节点只返回局部更新，由 LangGraph 合并为当前 State。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：API 层传入什么，load_context 如何初始化 State。
  slide.addText('1  从 API 层进入', {
    x: 0.62, y: 1.72, w: 1.8, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 0.62, y: 2.12, w: 2.85, h: 1.46,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('初始调用输入', {
    x: 0.86, y: 2.34, w: 1.0, h: 0.2,
    fontSize: 10, bold: true, color: C.navy, margin: 0
  });
  slide.addText('user_id', {
    x: 0.86, y: 2.7, w: 0.78, h: 0.16,
    fontFace: 'Consolas', fontSize: 8.2, bold: true, color: C.green, margin: 0
  });
  slide.addText('Session 注入的登录用户', {
    x: 1.67, y: 2.7, w: 1.42, h: 0.16,
    fontSize: 7.8, color: C.muted, margin: 0
  });
  slide.addText('request_id', {
    x: 0.86, y: 2.98, w: 0.78, h: 0.16,
    fontFace: 'Consolas', fontSize: 8.2, bold: true, color: C.teal, margin: 0
  });
  slide.addText('FastAPI 生成的请求标识', {
    x: 1.67, y: 2.98, w: 1.42, h: 0.16,
    fontSize: 7.8, color: C.muted, margin: 0
  });
  slide.addText('message', {
    x: 0.86, y: 3.26, w: 0.78, h: 0.16,
    fontFace: 'Consolas', fontSize: 8.2, bold: true, color: C.navy2, margin: 0
  });
  slide.addText('用户自然语言原文', {
    x: 1.67, y: 3.26, w: 1.42, h: 0.16,
    fontSize: 7.8, color: C.muted, margin: 0
  });

  slide.addShape(S.line, {
    x: 2.05, y: 3.58, w: 0, h: 0.31,
    line: { color: C.teal, width: 1.3, endArrowType: 'triangle' }
  });
  slide.addShape(S.roundRect, {
    x: 0.62, y: 3.91, w: 2.85, h: 2.3,
    rectRadius: 0.04,
    fill: { color: 'E9F1F7' }, line: { color: C.navy2, width: 1 }
  });
  slide.addText('load_context', {
    x: 0.86, y: 4.14, w: 1.1, h: 0.2,
    fontFace: 'Consolas', fontSize: 10, bold: true, color: C.navy2, margin: 0
  });
  const loadSteps = [
    ['01', '检查 user_id 与 request_id'],
    ['02', '清空旧 result、response、authorized'],
    ['03', '加载 account_id、balance、当日累计'],
    ['04', '写入 context_valid，决定是否继续']
  ];
  loadSteps.forEach((item, index) => {
    const y = 4.55 + index * 0.39;
    slide.addShape(S.ellipse, {
      x: 0.88, y, w: 0.27, h: 0.27,
      fill: { color: index === 3 ? C.teal : 'FFFFFF' },
      line: { color: C.teal, width: 0.9 }
    });
    slide.addText(item[0], {
      x: 0.88, y: y + 0.068, w: 0.27, h: 0.1,
      fontSize: 6.5, bold: true,
      color: index === 3 ? C.white : C.teal,
      align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 1.22, y: y + 0.025, w: 2.02, h: 0.18,
      fontSize: 7.2, color: C.ink, margin: 0, fit: 'shrink'
    });
  });
  slide.addText('节点只返回变更字段，LangGraph 负责与旧 State 合并。', {
    x: 0.82, y: 5.98, w: 2.5, h: 0.14,
    fontSize: 6.6, bold: true, color: C.navy, margin: 0
  });

  // 中栏：BankAgentState 全部 21 个字段及含义。
  slide.addText('2  State 包含哪些字段', {
    x: 3.78, y: 1.72, w: 2.3, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addText('21 个字段 · 4 组职责', {
    x: 7.2, y: 1.76, w: 1.25, h: 0.18,
    fontSize: 8.5, bold: true, color: C.teal, align: 'right', margin: 0
  });
  const stateSections = [
    {
      y: 2.12, h: 1.53, title: 'A  可信请求上下文', color: C.green, fill: 'E8F3EC',
      left: [
        ['user_id', '登录用户'], ['account_id', '付款账户'],
        ['request_id', '请求标识'], ['message', '用户原文']
      ],
      right: [
        ['daily_transfer_total', '当日累计'], ['balance', '可用余额'],
        ['context_valid', '上下文是否有效']
      ]
    },
    {
      y: 3.78, h: 1.08, title: 'B  模型候选理解', color: C.purple, fill: 'EFE9F6',
      left: [
        ['intent', '候选意图'], ['recipient_name', '候选姓名'], ['contact_id', '服务端联系人 ID']
      ],
      right: [
        ['amount', '候选金额'], ['missing_fields', '仍缺少的字段']
      ]
    },
    {
      y: 4.99, h: 1.2, title: 'C  计划与安全决策', color: C.amber, fill: 'FBF1D8',
      left: [
        ['plan', '结构化操作计划'], ['plan_valid', '计划校验结果'], ['risk_level', '四级风险']
      ],
      right: [
        ['operation_hash', '冻结操作参数'], ['challenge_id', '确认或认证挑战'], ['authorized', '服务端授权结果']
      ]
    },
    {
      y: 6.32, h: 0.64, title: 'D  执行与回复结果', color: C.navy2, fill: 'E9F1F7',
      left: [['status', '流程状态'], ['result', '结构化业务事实']],
      right: [['response', '用户回复']]
    }
  ];
  stateSections.forEach((section) => {
    slide.addShape(S.roundRect, {
      x: 3.78, y: section.y, w: 4.72, h: section.h,
      rectRadius: 0.035,
      fill: { color: section.fill }, line: { color: section.color, width: 1 }
    });
    slide.addText(section.title, {
      x: 4.0, y: section.y + 0.14, w: 1.75, h: 0.19,
      fontSize: 9.3, bold: true, color: section.color, margin: 0
    });
    const renderColumn = (items, x, startY) => {
      items.forEach((item, index) => {
        const y = startY + index * 0.25;
        slide.addText(item[0], {
          x, y, w: 1.23, h: 0.14,
          fontFace: 'Consolas', fontSize: 7.1, bold: true, color: C.ink,
          margin: 0, fit: 'shrink'
        });
        slide.addText(item[1], {
          x: x + 1.28, y, w: 0.72, h: 0.14,
          fontSize: 6.9, color: C.muted, margin: 0, fit: 'shrink'
        });
      });
    };
    renderColumn(section.left, 4.01, section.y + 0.48);
    renderColumn(section.right, 6.29, section.y + 0.48);
  });

  // 右栏：State 随节点推进而逐组补全。
  slide.addText('3  State 之后流向哪里', {
    x: 8.82, y: 1.72, w: 2.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const flowSteps = [
    ['理解与解析', '写入 intent、联系人、金额与缺失字段', C.purple, 'EFE9F6'],
    ['创建与校验计划', '写入 plan 与 plan_valid', C.navy2, 'E9F1F7'],
    ['安全策略', '写入 risk_level、hash 与 challenge', C.amber, 'FBF1D8'],
    ['中断或执行', '更新 authorized、status 与 result', C.green, 'E8F3EC'],
    ['组织回复', '只根据 result 写入 response', C.teal, 'E5F2F0']
  ];
  flowSteps.forEach((item, index) => {
    const y = 2.12 + index * 0.82;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.84, h: 0.61,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addShape(S.ellipse, {
      x: 9.04, y: y + 0.15, w: 0.31, h: 0.31,
      fill: { color: item[2] }, line: { color: item[2] }
    });
    slide.addText(String(index + 1), {
      x: 9.04, y: y + 0.225, w: 0.31, h: 0.11,
      fontSize: 6.8, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[0], {
      x: 9.51, y: y + 0.1, w: 1.35, h: 0.2,
      fontSize: 9.2, bold: true, color: C.ink, margin: 0
    });
    slide.addText(item[1], {
      x: 9.51, y: y + 0.33, w: 2.82, h: 0.15,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
    if (index < flowSteps.length - 1) {
      slide.addShape(S.line, {
        x: 10.74, y: y + 0.61, w: 0, h: 0.21,
        line: { color: '98A5AF', width: 1, endArrowType: 'triangle' }
      });
    }
  });

  slide.addShape(S.roundRect, {
    x: 8.82, y: 6.27, w: 3.84, h: 0.46,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('Checkpoint：State + 执行位置\nthread_id：查询键，不属于 State', {
    x: 9.03, y: 6.33, w: 3.42, h: 0.28,
    fontSize: 7.0, bold: true, color: C.navy, align: 'center', margin: 0
  });

  // 完整流程图改为外部超链接，避免挤压正文。
  slide.addShape(S.roundRect, {
    x: 8.82, y: 6.82, w: 3.84, h: 0.32,
    rectRadius: 0.03,
    fill: { color: C.navy }, line: { color: C.navy },
    hyperlink: {
      url: 'file:///C:/Users/SWF/Documents/deepseek-harness/default-workspace/bankagent/preparaion/assets/langgraph-full-flow.svg',
      tooltip: '打开完整节点 State I/O 流程图'
    }
  });
  slide.addText('打开完整节点 State I/O 流程图  ↗', {
    x: 8.82, y: 6.9, w: 3.84, h: 0.13,
    fontSize: 8.2, bold: true, color: C.white, align: 'center', margin: 0,
    hyperlink: {
      url: 'file:///C:/Users/SWF/Documents/deepseek-harness/default-workspace/bankagent/preparaion/assets/langgraph-full-flow.svg',
      tooltip: '打开完整节点 State I/O 流程图'
    }
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('07', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第八页：understand_intent 的输入、候选输出与信任边界
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('INTENT UNDERSTANDING', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('understand_intent：模型只输出候选，程序负责判断', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('该节点把 message 变成候选意图和候选参数，不查询余额、不批准操作、不执行转账。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：节点直接读取的可信输入。
  slide.addText('1  节点读取什么', {
    x: 0.62, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 0.62, y: 2.12, w: 3.17, h: 2.35,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('IN  state["message"]', {
    x: 0.86, y: 2.32, w: 2.2, h: 0.18,
    fontFace: 'Consolas', fontSize: 9.4, bold: true, color: C.green, margin: 0
  });
  slide.addText('用户自然语言原文；仍是不可信输入，只能被解析，不能被当作指令执行。', {
    x: 0.86, y: 2.6, w: 2.7, h: 0.5,
    fontSize: 8.2, color: C.muted, margin: 0, fit: 'shrink'
  });
  slide.addShape(S.line, {
    x: 0.86, y: 3.2, w: 2.7, h: 0,
    line: { color: C.line, width: 1 }
  });
  slide.addText('节点不读取', {
    x: 0.86, y: 3.32, w: 1.2, h: 0.18,
    fontSize: 8.6, bold: true, color: C.ink, margin: 0
  });
  slide.addText('balance · user_id · account_id\nrisk_level · authorized', {
    x: 0.86, y: 3.58, w: 2.7, h: 0.5,
    fontFace: 'Consolas', fontSize: 8.0, color: C.muted, margin: 0
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 4.61, w: 3.17, h: 1.87,
    rectRadius: 0.04,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('教学实现：规则 + 正则模拟模型', {
    x: 0.86, y: 4.81, w: 2.7, h: 0.18,
    fontSize: 9.0, bold: true, color: C.purple, margin: 0
  });
  slide.addText('余额 → BALANCE_QUERY\n转   → TRANSFER\n其他 → UNKNOWN', {
    x: 0.86, y: 5.11, w: 2.7, h: 0.72,
    fontFace: 'Consolas', fontSize: 8.4, color: C.ink, margin: 0
  });
  slide.addText('真实系统替换为结构化输出模型，输出形态与权限边界保持不变。', {
    x: 0.86, y: 5.9, w: 2.7, h: 0.42,
    fontSize: 7.8, color: C.muted, margin: 0, fit: 'shrink'
  });

  // 中栏：节点返回的结构化候选字段。
  slide.addText('2  节点输出什么', {
    x: 3.97, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addText('候选值，不是授权结果', {
    x: 6.0, y: 1.76, w: 2.55, h: 0.18,
    fontSize: 8.5, bold: true, color: C.purple, align: 'right', margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 3.97, y: 2.12, w: 4.58, h: 2.35,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 3.97, y: 2.12, w: 4.58, h: 0.44,
    fill: { color: C.navy2 }, line: { color: C.navy2 }
  });
  slide.addText('understand_intent(state) -> dict', {
    x: 4.2, y: 2.25, w: 3.6, h: 0.18,
    fontFace: 'Consolas', fontSize: 9.2, bold: true, color: C.white, margin: 0
  });
  slide.addText('{\n  "intent": "TRANSFER",\n  "recipient_name": "张伟",\n  "amount": 300.0,\n  "missing_fields": []\n}', {
    x: 4.2, y: 2.74, w: 4.12, h: 1.58,
    fontFace: 'Consolas', fontSize: 9.0, color: C.ink,
    margin: 0, valign: 'top', fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 3.97, y: 4.61, w: 4.58, h: 1.87,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('输出字段与约束', {
    x: 4.2, y: 4.79, w: 1.4, h: 0.18,
    fontSize: 9.2, bold: true, color: C.ink, margin: 0
  });
  const outFields = [
    ['intent', 'BALANCE_QUERY / TRANSFER / UNKNOWN'],
    ['recipient_name', '姓名候选，可能是搜索词或 None'],
    ['amount', '金额候选，float 仅用于教学'],
    ['missing_fields', 'recipient / amount / known_recipient']
  ];
  outFields.forEach((item, index) => {
    const y = 5.09 + index * 0.33;
    slide.addText(item[0], {
      x: 4.2, y, w: 1.3, h: 0.16,
      fontFace: 'Consolas', fontSize: 7.6, bold: true, color: C.navy2,
      margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 5.54, y, w: 2.8, h: 0.16,
      fontSize: 7.5, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  // 右栏：输出之后如何分流，以及模型不能决定什么。
  slide.addText('3  输出之后怎么走', {
    x: 8.82, y: 1.72, w: 2.5, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const intentBranches = [
    {
      color: C.purple, fill: 'EFE9F6',
      title: 'TRANSFER',
      desc: 'recipient_name 交给 resolve_entities 由服务端解析 contact_id'
    },
    {
      color: C.teal, fill: 'E5F2F0',
      title: 'BALANCE_QUERY',
      desc: 'missing_fields 为空，直接进入 create_plan 生成查询计划'
    },
    {
      color: C.amber, fill: 'FBF1D8',
      title: 'missing_fields 非空',
      desc: 'route_information 选择 clarify → ask_clarification 本轮结束'
    },
    {
      color: C.red, fill: 'F9E7E5',
      title: 'UNKNOWN',
      desc: '按不支持业务生成计划，由 validate_plan 拒绝，不猜测意图'
    }
  ];
  intentBranches.forEach((item, index) => {
    const y = 2.12 + index * 0.755;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.84, h: 0.62,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 9.06, y: y + 0.12, w: 3.36, h: 0.19,
      fontFace: 'Consolas', fontSize: 8.8, bold: true, color: item.color, margin: 0
    });
    slide.addText(item.desc, {
      x: 9.06, y: y + 0.34, w: 3.36, h: 0.2,
      fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
    });
  });
  slide.addText('下一个节点是 resolve_entities：姓名到 contact_id 的解析永远在服务端完成。', {
    x: 8.82, y: 5.17, w: 3.84, h: 0.18,
    fontSize: 7.4, italic: true, color: C.muted, margin: 0
  });

  slide.addShape(S.roundRect, {
    x: 8.82, y: 5.62, w: 3.84, h: 0.86,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('模型不能决定', {
    x: 9.06, y: 5.76, w: 1.4, h: 0.18,
    fontSize: 9.0, bold: true, color: C.red, margin: 0
  });
  slide.addText('本节点不查询余额、不校验限额、\n不批准操作、不执行任何转账。\n业务规则必须在服务端可信代码中再次校验。', {
    x: 9.06, y: 6.0, w: 3.36, h: 0.42,
    fontSize: 7.2, color: C.red, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.7, w: 11.99, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('信任边界：模型输出 = 候选意图与候选参数；Python 校验 = 决定是否执行；银行后端 = 修改真实状态', {
    x: 0.93, y: 6.79, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('08', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第九页：resolve_entities 的服务端实体解析与澄清分支
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('ENTITY RESOLUTION', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('resolve_entities：模型提出姓名，服务端给出联系人 ID', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('模型只能提供“张伟”这样的搜索词，contact_id 只能由服务端查询通讯录后写入。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：节点读取的候选字段与前置守卫。
  slide.addText('1  节点读取什么', {
    x: 0.62, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 0.62, y: 2.12, w: 3.17, h: 2.35,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('IN  候选与缺失字段', {
    x: 0.86, y: 2.32, w: 2.2, h: 0.18,
    fontFace: 'Consolas', fontSize: 9.4, bold: true, color: C.green, margin: 0
  });
  const entityInputs = [
    ['intent', '不是 TRANSFER 就直接返回空更新'],
    ['recipient_name', '模型给出的姓名，仅作搜索词'],
    ['missing_fields', '复制旧列表后再追加，不覆盖']
  ];
  entityInputs.forEach((item, index) => {
    const y = 2.66 + index * 0.52;
    slide.addText(item[0], {
      x: 0.86, y, w: 2.7, h: 0.16,
      fontFace: 'Consolas', fontSize: 7.8, bold: true, color: C.navy2,
      margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 0.86, y: y + 0.2, w: 2.7, h: 0.24,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 4.67, w: 3.17, h: 1.81,
    rectRadius: 0.04,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('教学实现：CONTACTS 字典模拟通讯录', {
    x: 0.86, y: 4.87, w: 2.7, h: 0.18,
    fontSize: 8.6, bold: true, color: C.purple, margin: 0
  });
  slide.addText('"张伟": "contact-001"\n"李娜": "contact-002"', {
    x: 0.86, y: 5.15, w: 2.7, h: 0.45,
    fontFace: 'Consolas', fontSize: 8.2, color: C.ink, margin: 0
  });
  slide.addText('真实系统应调用通讯录服务，并处理重名、手机号尾号等歧义；查不到不等于可以新建收款人。', {
    x: 0.86, y: 5.73, w: 2.7, h: 0.62,
    fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
  });

  // 中栏：解析过程与写入 State 的字段。
  slide.addText('2  节点输出什么', {
    x: 3.97, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addText('写回服务端解析结果', {
    x: 6.0, y: 1.76, w: 2.55, h: 0.18,
    fontSize: 8.5, bold: true, color: C.purple, align: 'right', margin: 0
  });

  const resolveSteps = [
    ['01', '判断 intent 是否为 TRANSFER，否则本轮不做解析'],
    ['02', '用 recipient_name 作为搜索词查询服务端通讯录'],
    ['03', '命中唯一联系人：写入 contact_id'],
    ['04', '姓名为空或查不到：追加 known_recipient 到缺失字段']
  ];
  resolveSteps.forEach((item, index) => {
    const y = 2.12 + index * 0.62;
    slide.addShape(S.roundRect, {
      x: 3.97, y, w: 4.58, h: 0.53,
      rectRadius: 0.04,
      fill: { color: index === 3 ? 'FBF1D8' : 'FFFFFF' },
      line: { color: index === 3 ? C.amber : 'C8D4DE', width: 1 }
    });
    slide.addShape(S.ellipse, {
      x: 4.15, y: y + 0.13, w: 0.26, h: 0.26,
      fill: { color: index === 3 ? C.amber : C.navy2 },
      line: { color: index === 3 ? C.amber : C.navy2 }
    });
    slide.addText(item[0], {
      x: 4.15, y: y + 0.195, w: 0.26, h: 0.1,
      fontSize: 6.5, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 4.52, y: y + 0.14, w: 3.85, h: 0.2,
      fontSize: 8.0, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 3.97, y: 4.67, w: 4.58, h: 1.81,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 3.97, y: 4.67, w: 4.58, h: 0.44,
    fill: { color: C.navy2 }, line: { color: C.navy2 }
  });
  slide.addText('return {"contact_id": ..., "missing_fields": ...}', {
    x: 4.2, y: 4.8, w: 4.12, h: 0.18,
    fontFace: 'Consolas', fontSize: 8.6, bold: true, color: C.white, margin: 0
  });
  const entityOutputs = [
    ['contact_id', '服务端内部 ID；查不到时为 None，绝不由模型填写'],
    ['missing_fields', '追加 known_recipient 后交给路由判断']
  ];
  entityOutputs.forEach((item, index) => {
    const y = 5.25 + index * 0.48;
    slide.addText(item[0], {
      x: 4.2, y, w: 1.35, h: 0.16,
      fontFace: 'Consolas', fontSize: 7.6, bold: true, color: C.navy2,
      margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 5.6, y: y - 0.015, w: 2.75, h: 0.3,
      fontSize: 7.3, color: C.muted, margin: 0, fit: 'shrink'
    });
  });
  slide.addText('输出只有一个联系人 ID 和缺失字段；余额、限额、风控都不在此节点判断。', {
    x: 4.2, y: 6.2, w: 4.12, h: 0.16,
    fontSize: 7.2, italic: true, color: C.muted, margin: 0
  });

  // 右栏：条件边分流与信任边界。
  slide.addText('3  输出之后怎么走', {
    x: 8.82, y: 1.72, w: 2.5, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const entityBranches = [
    {
      color: C.teal, fill: 'E5F2F0',
      title: 'missing_fields 为空',
      desc: 'route_information 返回 create_plan，进入计划阶段'
    },
    {
      color: C.amber, fill: 'FBF1D8',
      title: 'missing_fields 非空',
      desc: 'route_information 返回 clarify → ask_clarification'
    },
    {
      color: C.navy2, fill: 'E9F1F7',
      title: 'ask_clarification',
      desc: '把内部字段名翻译成“收款人”“金额”等用户可读提示'
    },
    {
      color: C.red, fill: 'F9E7E5',
      title: '本轮结束（END）',
      desc: '澄清不是 resume；下一轮是同一 thread 的新 invoke'
    }
  ];
  entityBranches.forEach((item, index) => {
    const y = 2.12 + index * 0.755;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.84, h: 0.62,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 9.06, y: y + 0.12, w: 3.36, h: 0.19,
      fontSize: 8.8, bold: true, color: item.color, margin: 0, fit: 'shrink'
    });
    slide.addText(item.desc, {
      x: 9.06, y: y + 0.34, w: 3.36, h: 0.2,
      fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
    });
  });
  slide.addText('澄清提示只说明缺什么，不替用户猜默认收款人或默认金额。', {
    x: 8.82, y: 5.17, w: 3.84, h: 0.18,
    fontSize: 7.4, italic: true, color: C.muted, margin: 0
  });

  slide.addShape(S.roundRect, {
    x: 8.82, y: 5.62, w: 3.84, h: 0.86,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('模型的越界可能', {
    x: 9.06, y: 5.76, w: 1.6, h: 0.18,
    fontSize: 9.0, bold: true, color: C.red, margin: 0
  });
  slide.addText('模型若自行编造 contact_id，本节点会用服务端查询结果覆盖它。\n转账仍必须另行确认；联系人 ID 不代表身份已核验。', {
    x: 9.06, y: 6.0, w: 3.36, h: 0.42,
    fontSize: 7.2, color: C.red, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.7, w: 11.99, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('信任边界：姓名是模型候选，contact_id 是服务端事实；查不到就澄清，不新建、不猜测、不默认', {
    x: 0.93, y: 6.79, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('09', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第十页：create_plan 与 validate_plan，计划如何被确定性地校验
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('PLAN & VALIDATION', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('create_plan 与 validate_plan：计划由程序校验，不靠模型自我批准', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('候选意图先映射成白名单内的结构化计划，再用确定性 Python 规则判断它是否有效。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：意图到操作的映射表。
  slide.addText('1  create_plan 生成什么', {
    x: 0.62, y: 1.72, w: 2.6, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 0.62, y: 2.12, w: 3.17, h: 2.35,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('意图 → 操作的固定映射', {
    x: 0.86, y: 2.32, w: 2.2, h: 0.18,
    fontSize: 8.8, bold: true, color: C.ink, margin: 0
  });
  const planMapping = [
    ['BALANCE_QUERY', 'GET_BALANCE', C.green, 'E8F3EC', '参数为空'],
    ['TRANSFER', 'PREPARE_TRANSFER', C.amber, 'FBF1D8', 'contact_id、amount、currency'],
    ['UNKNOWN', 'UNSUPPORTED', C.red, 'F9E7E5', '交由白名单拒绝']
  ];
  planMapping.forEach((item, index) => {
    const y = 2.62 + index * 0.6;
    slide.addShape(S.roundRect, {
      x: 0.84, y, w: 2.73, h: 0.52,
      rectRadius: 0.035,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 0.98, y: y + 0.07, w: 1.2, h: 0.16,
      fontFace: 'Consolas', fontSize: 7.2, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText('→  ' + item[1], {
      x: 0.98, y: y + 0.27, w: 2.45, h: 0.16,
      fontFace: 'Consolas', fontSize: 7.6, bold: true, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 4.61, w: 3.17, h: 1.87,
    rectRadius: 0.04,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('白名单只有两项', {
    x: 0.86, y: 4.79, w: 2.2, h: 0.18,
    fontSize: 9.0, bold: true, color: C.purple, margin: 0
  });
  slide.addText('ALLOWED_OPERATIONS =\n{ "GET_BALANCE",\n  "PREPARE_TRANSFER" }', {
    x: 0.86, y: 5.07, w: 2.7, h: 0.66,
    fontFace: 'Consolas', fontSize: 7.8, color: C.ink, margin: 0
  });
  slide.addText('模型只能提出和准备转账，白名单里没有 execute_transfer，所以模型没有直接执行能力。', {
    x: 0.86, y: 5.82, w: 2.7, h: 0.55,
    fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
  });

  // 中栏：计划的真实数据结构。
  slide.addText('2  计划长什么样', {
    x: 3.97, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addText('一条计划 = 一个操作', {
    x: 6.0, y: 1.76, w: 2.55, h: 0.18,
    fontSize: 8.5, bold: true, color: C.purple, align: 'right', margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 3.97, y: 2.12, w: 4.58, h: 2.35,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 3.97, y: 2.12, w: 4.58, h: 0.44,
    fill: { color: C.navy2 }, line: { color: C.navy2 }
  });
  slide.addText('state["plan"]', {
    x: 4.2, y: 2.25, w: 2.4, h: 0.18,
    fontFace: 'Consolas', fontSize: 9.2, bold: true, color: C.white, margin: 0
  });
  slide.addText('[\n  {\n    "operation": "PREPARE_TRANSFER",\n    "parameters": {\n      "contact_id": "contact-001",\n      "amount": 300,\n      "currency": "CNY"\n    }\n  }\n]', {
    x: 4.2, y: 2.68, w: 4.12, h: 1.66,
    fontFace: 'Consolas', fontSize: 7.6, color: C.ink,
    margin: 0, valign: 'top', fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 3.97, y: 4.61, w: 4.58, h: 0.66,
    rectRadius: 0.04,
    fill: { color: 'FBF1D8' }, line: { color: C.amber, width: 1 }
  });
  slide.addText('转账计划里的 contact_id 来自上一个节点的服务端解析，不是模型填的。', {
    x: 4.2, y: 4.76, w: 4.12, h: 0.38,
    fontSize: 7.8, color: C.ink, margin: 0, fit: 'shrink'
  });

  // 中栏：确定性校验规则。
  slide.addText('3  validate_plan 校验什么', {
    x: 3.97, y: 5.4, w: 3.2, h: 0.28,
    fontSize: 12.5, bold: true, color: C.ink, margin: 0
  });
  const validRules = [
    ['规则 1', '计划只能包含一个操作，且操作必须在白名单内'],
    ['规则 2', '转账计划还必须有正数 amount 和非空 contact_id']
  ];
  validRules.forEach((item, index) => {
    const y = 5.74 + index * 0.37;
    slide.addShape(S.roundRect, {
      x: 3.97, y, w: 4.58, h: 0.32,
      rectRadius: 0.03,
      fill: { color: index === 1 ? 'FBF1D8' : 'FFFFFF' },
      line: { color: index === 1 ? C.amber : 'C8D4DE', width: 1 }
    });
    slide.addText(item[0], {
      x: 4.15, y: y + 0.075, w: 0.62, h: 0.17,
      fontSize: 7.4, bold: true, color: index === 1 ? C.amber : C.navy2, margin: 0
    });
    slide.addText(item[1], {
      x: 4.79, y: y + 0.065, w: 3.6, h: 0.19,
      fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 右栏：校验结果与分流。
  slide.addText('4  plan_valid 决定去哪', {
    x: 8.82, y: 1.72, w: 2.8, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 8.82, y: 2.12, w: 3.84, h: 1.6,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addText('route_plan(state)', {
    x: 9.06, y: 2.28, w: 2.6, h: 0.18,
    fontFace: 'Consolas', fontSize: 9.2, bold: true, color: C.navy, margin: 0
  });
  slide.addText('return "security" if state.get("plan_valid") else "reject"', {
    x: 9.06, y: 2.56, w: 3.36, h: 0.36,
    fontFace: 'Consolas', fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
  });
  slide.addText('路由函数只读 plan_valid，不修改 State，也不做校验本身。', {
    x: 9.06, y: 3.0, w: 3.36, h: 0.28,
    fontSize: 7.4, italic: true, color: C.muted, margin: 0, fit: 'shrink'
  });
  slide.addText('plan_valid = true\nplan_valid = false', {
    x: 9.06, y: 3.3, w: 1.6, h: 0.32,
    fontFace: 'Consolas', fontSize: 7.6, color: C.ink, margin: 0
  });

  const planBranches = [
    {
      color: C.green, fill: 'E8F3EC',
      title: '→ security_policy',
      desc: 'plan_valid 为真，进入风险定级；此时仍未授权、未查余额'
    },
    {
      color: C.red, fill: 'F9E7E5',
      title: '→ reject_plan',
      desc: 'status = REJECTED，result.reason = unsupported_or_invalid_plan'
    }
  ];
  planBranches.forEach((item, index) => {
    const y = 3.9 + index * 0.88;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.84, h: 0.8,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 9.06, y: y + 0.11, w: 3.36, h: 0.19,
      fontFace: 'Consolas', fontSize: 8.8, bold: true, color: item.color, margin: 0
    });
    slide.addText(item.desc, {
      x: 9.06, y: y + 0.34, w: 3.36, h: 0.36,
      fontSize: 7.3, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 8.82, y: 5.74, w: 3.84, h: 0.74,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('plan_valid 只代表“格式与基础参数有效”', {
    x: 9.06, y: 5.86, w: 3.36, h: 0.18,
    fontSize: 8.4, bold: true, color: C.red, margin: 0, fit: 'shrink'
  });
  slide.addText('它不代表用户已授权，也不代表余额和风控已通过；那三项在后续节点才判断。', {
    x: 9.06, y: 6.09, w: 3.36, h: 0.3,
    fontSize: 7.3, color: C.red, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.7, w: 11.99, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('信任边界：计划由程序按白名单生成与校验；模型既不产生操作名白名单，也不能把自己的输出认定为有效', {
    x: 0.93, y: 6.79, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('10', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第十一页：security_policy 的四级风险定级与四条分支
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('SECURITY POLICY', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('security_policy：风险等级由程序判定，不由模型决定', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('四个等级各对应一条条件边；模型既不参与定级，也无法改变判定结果。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：四个风险等级。
  slide.addText('1  四个等级', {
    x: 0.62, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const riskLevels = [
    ['GREEN', 'GET_BALANCE 只读查询', C.green, 'E8F3EC'],
    ['YELLOW', '转账，当日累计 + 本次 ≤ 1000', C.amber, 'FBF1D8'],
    ['RED', '转账，当日累计 + 本次 > 1000', C.red, 'F9E7E5'],
    ['DENY', '单笔 > 10000，或非转账写操作', '8A5A55', 'EFE3E1']
  ];
  riskLevels.forEach((item, index) => {
    const y = 2.12 + index * 0.73;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 3.17, h: 0.64,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 0.86, y: y + 0.11, w: 1.2, h: 0.2,
      fontFace: 'Consolas', fontSize: 10, bold: true, color: item[2], margin: 0
    });
    slide.addText(item[1], {
      x: 0.86, y: y + 0.34, w: 2.7, h: 0.2,
      fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 5.12, w: 3.17, h: 1.36,
    rectRadius: 0.04,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('0 是测试用的两分钟捷径', {
    x: 0.86, y: 5.3, w: 2.7, h: 0.18,
    fontSize: 8.4, bold: true, color: C.purple, margin: 0
  });
  slide.addText('退出 col2 直接判 DENY，不用 col1 的控制流，也不用 col0 的辅助函数。', {
    x: 0.86, y: 5.56, w: 2.7, h: 0.3,
    fontSize: 7.3, color: C.muted, margin: 0, fit: 'shrink'
  });
  slide.addText('所以定级最少要读到 plan[0]，这就是它排在校验之后的原因。', {
    x: 0.86, y: 6.0, w: 2.7, h: 0.42,
    fontSize: 7.3, color: C.muted, margin: 0, fit: 'shrink'
  });

  // 中栏：判定规则的源码形态。
  slide.addText('2  判定规则', {
    x: 3.97, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addText('三条判断按顺序短路', {
    x: 6.0, y: 1.76, w: 2.55, h: 0.18,
    fontSize: 8.5, bold: true, color: C.purple, align: 'right', margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 3.97, y: 2.12, w: 4.58, h: 2.35,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 3.97, y: 2.12, w: 4.58, h: 0.44,
    fill: { color: C.navy2 }, line: { color: C.navy2 }
  });
  slide.addText('operation = state["plan"][0]["operation"]', {
    x: 4.2, y: 2.25, w: 4.12, h: 0.18,
    fontFace: 'Consolas', fontSize: 8.6, bold: true, color: C.white, margin: 0
  });
  slide.addText('if operation == "GET_BALANCE":\n    return {"risk_level": "GREEN"}\n\nif operation != "PREPARE_TRANSFER":\n    return {"risk_level": "DENY"}\n\nprojected = state["daily_transfer_total"] + amount\nif amount > 10_000:\n    return {"risk_level": "DENY"}\nreturn {"risk_level": "YELLOW" if projected <= 1000 else "RED"}', {
    x: 4.2, y: 2.68, w: 4.12, h: 1.66,
    fontFace: 'Consolas', fontSize: 7.0, color: C.ink,
    margin: 0, valign: 'top', fit: 'shrink'
  });

  const policyNotes = [
    ['两个阈值', '单笔 10000 直接 DENY；当日累计 1000 区分黄与红'],
    ['阈值是教学值', '真实系统应来自版本化策略配置，不能写死在代码里']
  ];
  policyNotes.forEach((item, index) => {
    const y = 4.61 + index * 0.66;
    slide.addShape(S.roundRect, {
      x: 3.97, y, w: 4.58, h: 0.58,
      rectRadius: 0.04,
      fill: { color: index === 1 ? 'FBF1D8' : 'FFFFFF' },
      line: { color: index === 1 ? C.amber : 'C8D4DE', width: 1 }
    });
    slide.addText(item[0], {
      x: 4.2, y: y + 0.1, w: 1.3, h: 0.18,
      fontSize: 8.6, bold: true, color: index === 1 ? C.amber : C.navy2, margin: 0
    });
    slide.addText(item[1], {
      x: 4.2, y: y + 0.31, w: 4.12, h: 0.2,
      fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  // 右栏：路由函数与四条边。
  slide.addText('3  route_security 生成四条边', {
    x: 8.82, y: 1.72, w: 3.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 8.82, y: 2.12, w: 3.84, h: 1.72,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addText('return {', {
    x: 9.06, y: 2.26, w: 2.6, h: 0.16,
    fontFace: 'Consolas', fontSize: 7.6, bold: true, color: C.navy, margin: 0
  });
  slide.addText('    "GREEN":  "green",\n    "YELLOW": "yellow",\n    "RED":    "red",\n    "DENY":   "deny",\n}[state["risk_level"]]', {
    x: 9.06, y: 2.44, w: 3.36, h: 0.96,
    fontFace: 'Consolas', fontSize: 7.6, color: C.ink, margin: 0, valign: 'top'
  });
  slide.addText('用字典把等级映射成路径名，四个出口一眼可数；缺字段会直接报错，不会静默通过。', {
    x: 9.06, y: 3.42, w: 3.36, h: 0.32,
    fontSize: 7.3, color: C.muted, margin: 0, fit: 'shrink'
  });

  const edgeTargets = [
    ['green  →  execute_query', '只读查询，直接执行', C.green, 'E8F3EC'],
    ['yellow →  interrupt_for_confirmation', '暂停，等用户确认', C.amber, 'FBF1D8'],
    ['red    →  interrupt_for_authentication', '暂停，等强认证', C.red, 'F9E7E5'],
    ['deny   →  reject_operation', '直接拒绝，不进中断', '8A5A55', 'EFE3E1']
  ];
  edgeTargets.forEach((item, index) => {
    const y = 3.96 + index * 0.62;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.84, h: 0.54,
      rectRadius: 0.035,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 9.04, y: y + 0.07, w: 3.4, h: 0.18,
      fontFace: 'Consolas', fontSize: 7.4, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 9.04, y: y + 0.28, w: 3.4, h: 0.18,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.7, w: 11.99, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('风险等级是程序算出来的；提示注入、越权声明或模型自信都不能改变它', {
    x: 0.93, y: 6.79, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.red, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('11', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第十二页：operation_hash 与 challenge_id 的绑定
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('OPERATION BINDING', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('挑战绑定：一旦确认，这次操作的参数就不能再变', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('security_policy 对写操作额外生成两个字段：一个冻结参数，一个标识本次挑战。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：哈希包含哪些字段。
  slide.addText('1  哈希里放了什么', {
    x: 0.62, y: 1.72, w: 2.6, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const hashFields = [
    ['user_id', '谁在操作'],
    ['account_id', '从哪个账户出钱'],
    ['contact_id', '转账给谁'],
    ['amount', '转多少'],
    ['currency', '什么币种'],
    ['request_id', '哪一次请求']
  ];
  hashFields.forEach((item, index) => {
    const col = index % 2;
    const row = Math.floor(index / 2);
    const x = 0.62 + col * 1.63;
    const y = 2.12 + row * 0.42;
    slide.addText(item[0], {
      x, y, w: 1.55, h: 0.16,
      fontFace: 'Consolas', fontSize: 7.4, bold: true, color: C.navy2, margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x, y: y + 0.16, w: 1.55, h: 0.16,
      fontSize: 6.9, color: C.muted, margin: 0, fit: 'shrink'
    });
  });
  slide.addShape(S.line, {
    x: 0.62, y: 3.46, w: 3.17, h: 0,
    line: { color: C.line, width: 1 }
  });
  slide.addText('六个字段一旦入哈希，任何一个被改动，哈希就完全不同。', {
    x: 0.62, y: 3.58, w: 3.17, h: 0.4,
    fontSize: 7.6, color: C.muted, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 4.12, w: 3.17, h: 2.36,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('operation_hash 的生成', {
    x: 0.86, y: 4.3, w: 2.4, h: 0.18,
    fontSize: 8.8, bold: true, color: C.ink, margin: 0
  });
  slide.addText('payload = {\n  "user_id": ...,\n  "account_id": ...,\n  "contact_id": ...,\n  "amount": ...,\n  "currency": "CNY",\n  "request_id": ...,\n}\nhashlib.sha256(\n  json.dumps(payload,\n    sort_keys=True)\n  .encode("utf-8")\n).hexdigest()', {
    x: 0.86, y: 4.56, w: 2.7, h: 1.8,
    fontFace: 'Consolas', fontSize: 7.0, color: C.ink,
    margin: 0, valign: 'top', fit: 'shrink'
  });

  // 中栏：绑定关系与两种字段。
  slide.addText('2  两个字段各管什么', {
    x: 3.97, y: 1.72, w: 2.6, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const twoFields = [
    {
      name: 'operation_hash', color: C.amber, fill: 'FBF1D8',
      desc: '把这次操作的全部参数冻结成一个指纹。恢复时若参数被替换，指纹必然对不上。'
    },
    {
      name: 'challenge_id', color: C.teal, fill: 'E5F2F0',
      desc: '这次挑战的编号，由 request_id 派生：challenge-{request_id}。它回答“你确认的是哪一次挑战”。'
    }
  ];
  twoFields.forEach((item, index) => {
    const y = 2.12 + index * 1.3;
    slide.addShape(S.roundRect, {
      x: 3.97, y, w: 4.58, h: 1.16,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.name, {
      x: 4.2, y: y + 0.14, w: 3.0, h: 0.2,
      fontFace: 'Consolas', fontSize: 9.6, bold: true, color: item.color, margin: 0
    });
    slide.addText(item.desc, {
      x: 4.2, y: y + 0.42, w: 4.12, h: 0.62,
      fontSize: 8.0, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 3.97, y: 4.72, w: 4.58, h: 1.76,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('没有它会发生什么', {
    x: 4.2, y: 4.9, w: 2.2, h: 0.2,
    fontSize: 9.4, bold: true, color: C.red, margin: 0
  });
  slide.addText('用户确认“给张伟转 300 元”之后，如果参数能在确认与执行之间被替换成 3 万元，人审就形同虚设。哈希把“确认的内容”和“执行的内容”锁成同一个对象。', {
    x: 4.2, y: 5.18, w: 4.12, h: 1.2,
    fontSize: 8.2, color: C.red, margin: 0, fit: 'shrink'
  });

  // 右栏：绑定关系示意。
  slide.addText('3  绑定关系', {
    x: 8.82, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 8.82, y: 2.12, w: 3.84, h: 4.36,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  const bindSteps = [
    ['1', '用户发起转账', 'security_policy 生成哈希与挑战', C.navy2],
    ['2', '展示给用户', '界面拿到 recipient、amount 与哈希', C.teal],
    ['3', '用户点确认', '外部提交 approved + 两个字段', C.amber],
    ['4', '恢复并核对', '三个条件同时匹配才算授权', C.green],
    ['5', '进入执行', '执行前还会再复检一次', C.navy2]
  ];
  bindSteps.forEach((item, index) => {
    const y = 2.34 + index * 0.8;
    slide.addShape(S.ellipse, {
      x: 9.06, y, w: 0.32, h: 0.32,
      fill: { color: item[3] }, line: { color: item[3] }
    });
    slide.addText(item[0], {
      x: 9.06, y: y + 0.075, w: 0.32, h: 0.12,
      fontSize: 7.4, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 9.5, y: y + 0.02, w: 3.0, h: 0.19,
      fontSize: 9.0, bold: true, color: C.ink, margin: 0
    });
    slide.addText(item[2], {
      x: 9.5, y: y + 0.22, w: 3.0, h: 0.19,
      fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
    });
    if (index < bindSteps.length - 1) {
      slide.addShape(S.line, {
        x: 9.22, y: y + 0.32, w: 0, h: 0.48,
        line: { color: '98A5AF', width: 1, endArrowType: 'triangle' }
      });
    }
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.7, w: 11.99, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('确认的对象是“这一组参数”，不是“这个意图”；参数变了就必须重新确认', {
    x: 0.93, y: 6.79, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.17, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('12', {
    x: 12.55, y: 7.15, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第十三页：interrupt 暂停与 resume 恢复（合并页）
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('INTERRUPT & RESUME', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('interrupt 与 resume：流程如何暂停，以及恢复时会发生什么', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('这一页是全篇最需要记住的机制：暂停靠 interrupt，恢复靠同 thread 的 resume，而节点会从头重跑。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：两个中断节点的展示载荷。
  slide.addText('1  暂停时对外展示什么', {
    x: 0.62, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const interrupts = [
    {
      title: 'interrupt_for_confirmation', color: C.amber, fill: 'FBF1D8',
      code: '{\n  "kind": "CONFIRMATION",\n  "challenge_id": ...,\n  "operation_hash": ...,\n  "recipient": "张伟",\n  "amount": 300\n}'
    },
    {
      title: 'interrupt_for_authentication', color: C.red, fill: 'F9E7E5',
      code: '{\n  "kind": "STRONG_AUTH",\n  "challenge_id": ...,\n  "operation_hash": ...,\n  "methods": ["OTP", "FACE"],\n  "amount": 300\n}'
    }
  ];
  interrupts.forEach((item, index) => {
    const y = 2.12 + index * 1.62;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 3.17, h: 1.48,
      rectRadius: 0.04,
      fill: { color: 'FFFFFF' }, line: { color: item.color, width: 1.1 }
    });
    slide.addShape(S.rect, {
      x: 0.62, y, w: 3.17, h: 0.36,
      fill: { color: item.color }, line: { color: item.color }
    });
    slide.addText(item.title, {
      x: 0.82, y: y + 0.09, w: 2.8, h: 0.18,
      fontFace: 'Consolas', fontSize: 7.6, bold: true, color: C.white, margin: 0, fit: 'shrink'
    });
    slide.addText(item.code, {
      x: 0.82, y: y + 0.44, w: 2.78, h: 0.96,
      fontFace: 'Consolas', fontSize: 7.0, color: C.ink,
      margin: 0, valign: 'top', fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 5.36, w: 3.17, h: 1.12,
    rectRadius: 0.04,
    fill: { color: 'E8F3EC' }, line: { color: C.green, width: 1 }
  });
  slide.addText('载荷里永远没有的东西', {
    x: 0.86, y: 5.52, w: 2.5, h: 0.18,
    fontSize: 8.6, bold: true, color: C.green, margin: 0
  });
  slide.addText('OTP、支付密码、生物特征、令牌都不进入展示载荷，也不写入 State、Checkpoint 或日志；强认证由独立服务完成。', {
    x: 0.86, y: 5.76, w: 2.7, h: 0.62,
    fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
  });

  // 中栏：恢复语义。
  slide.addText('2  恢复时怎么判断放行', {
    x: 3.97, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addText('黄色：三个条件同时匹配', {
    x: 3.97, y: 2.12, w: 4.58, h: 0.2,
    fontSize: 9.0, bold: true, color: C.amber, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 3.97, y: 2.36, w: 4.58, h: 1.16,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('decision["approved"] is True\nand decision["challenge_id"] == state["challenge_id"]\nand decision["operation_hash"] == state["operation_hash"]', {
    x: 4.18, y: 2.48, w: 4.16, h: 0.92,
    fontFace: 'Consolas', fontSize: 7.0, color: C.ink,
    margin: 0, valign: 'top', fit: 'shrink'
  });
  slide.addText('红色：把 token 换成一次服务端查询', {
    x: 3.97, y: 3.62, w: 4.58, h: 0.2,
    fontSize: 9.0, bold: true, color: C.red, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 3.97, y: 3.86, w: 4.58, h: 1.0,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('教学版比较固定字符串 demo-otp-ok；真实系统必须查询独立认证服务签发的短期凭证，而不是把令牌传回图里比较。', {
    x: 4.18, y: 3.98, w: 4.16, h: 0.76,
    fontSize: 7.6, color: C.red, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 3.97, y: 4.98, w: 4.58, h: 1.5,
    rectRadius: 0.04,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('恢复载荷只是“用户说了什么”', {
    x: 4.18, y: 5.14, w: 4.16, h: 0.2,
    fontSize: 8.8, bold: true, color: C.purple, margin: 0
  });
  slide.addText('它不是授权记录。真实系统还应验证当前登录用户，并从服务端确认表读取不可伪造的授权结果——载荷可被构造，服务端记录不能。', {
    x: 4.18, y: 5.4, w: 4.16, h: 0.96,
    fontSize: 7.8, color: C.ink, margin: 0, fit: 'shrink'
  });

  // 右栏：重跑语义。
  slide.addText('3  恢复时节点会重跑', {
    x: 8.82, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 8.82, y: 2.12, w: 3.84, h: 1.66,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1.1 }
  });
  slide.addText('含 interrupt 的节点从函数开头重新执行', {
    x: 9.06, y: 2.28, w: 3.36, h: 0.36,
    fontSize: 9.0, bold: true, color: C.red, margin: 0, fit: 'shrink'
  });
  slide.addText('恢复不是从 interrupt 那一行继续，而是整个节点重跑一遍；此时 interrupt() 的返回值换成了外部提交的决定。', {
    x: 9.06, y: 2.7, w: 3.36, h: 0.62,
    fontSize: 7.8, color: C.red, margin: 0, fit: 'shrink'
  });
  slide.addText('推论：interrupt 之前绝不能有不可重复的副作用——发短信、扣款、生成流水号都不行。', {
    x: 9.06, y: 3.36, w: 3.36, h: 0.36,
    fontSize: 7.8, bold: true, color: C.red, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 8.82, y: 3.92, w: 3.84, h: 1.2,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('设计上把副作用后排', {
    x: 9.06, y: 4.06, w: 3.36, h: 0.18,
    fontSize: 8.6, bold: true, color: C.ink, margin: 0
  });
  slide.addText('确认与认证只负责得到 authorized；真正的状态修改集中在 execute_operation 一个节点，重跑它也不会重复扣款（靠幂等键兜底）。', {
    x: 9.06, y: 4.3, w: 3.36, h: 0.72,
    fontSize: 7.6, color: C.muted, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 8.82, y: 5.26, w: 3.84, h: 1.22,
    rectRadius: 0.04,
    fill: { color: 'E5F2F0' }, line: { color: C.teal, width: 1 }
  });
  slide.addText('恢复需要什么', {
    x: 9.06, y: 5.4, w: 2.4, h: 0.18,
    fontSize: 8.8, bold: true, color: C.teal, margin: 0
  });
  slide.addText('同一个 thread_id + Command(resume=...)。thread_id 相同才能找到原来那份 Checkpoint；换线程就是另起一次对话。', {
    x: 9.06, y: 5.64, w: 3.36, h: 0.72,
    fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.66, w: 11.99, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('中断前不要有副作用；恢复时节点会从头重跑；授权要读服务端记录，不要相信恢复载荷', {
    x: 0.93, y: 6.75, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.14, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('13', {
    x: 12.55, y: 7.12, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第十四页：execute_operation 与收尾
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('EXECUTION', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('execute_operation：真实状态只在最后一个节点被修改', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('路由已经判断过授权，执行节点仍然要再查一次；因为这是修改真实状态的最后一道门。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：执行节点的判定顺序。
  slide.addText('1  执行前复检什么', {
    x: 0.62, y: 1.72, w: 2.6, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const execChecks = [
    ['01', 'authorized 仍为真，否则 missing_authorization', C.red, 'F9E7E5'],
    ['02', '重新读取余额，amount > balance 则失败', C.amber, 'FBF1D8'],
    ['03', '写入 COMPLETED 与 remaining_balance', C.green, 'E8F3EC']
  ];
  execChecks.forEach((item, index) => {
    const y = 2.12 + index * 0.78;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 3.17, h: 0.68,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addShape(S.ellipse, {
      x: 0.84, y: y + 0.19, w: 0.3, h: 0.3,
      fill: { color: item[2] }, line: { color: item[2] }
    });
    slide.addText(item[0], {
      x: 0.84, y: y + 0.27, w: 0.3, h: 0.12,
      fontSize: 6.8, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 1.24, y: y + 0.1, w: 2.4, h: 0.48,
      fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 4.52, w: 3.17, h: 1.96,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('三种出口结果', {
    x: 0.86, y: 4.7, w: 2.0, h: 0.18,
    fontSize: 8.8, bold: true, color: C.ink, margin: 0
  });
  const execOutcomes = [
    ['COMPLETED', '转账成功，附 remaining_balance'],
    ['FAILED', 'insufficient_balance，余额不足'],
    ['REJECTED', 'missing_authorization，授权缺失']
  ];
  execOutcomes.forEach((item, index) => {
    const y = 4.98 + index * 0.46;
    slide.addText(item[0], {
      x: 0.86, y, w: 1.2, h: 0.16,
      fontFace: 'Consolas', fontSize: 7.4, bold: true, color: C.navy2, margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 0.86, y: y + 0.17, w: 2.7, h: 0.18,
      fontSize: 7.0, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：reject_operation 的收敛作用。
  slide.addText('2  reject_operation 统一收口', {
    x: 3.97, y: 1.72, w: 3.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addText('四类来源汇入同一个节点', {
    x: 6.0, y: 1.76, w: 2.55, h: 0.18,
    fontSize: 8.5, bold: true, color: C.purple, align: 'right', margin: 0
  });
  const rejectSources = [
    ['DENY 策略拒绝', '金额超阈值或非白名单写操作'],
    ['用户拒绝确认', 'approved 为假'],
    ['挑战不匹配', 'challenge_id 或 operation_hash 对不上'],
    ['强认证失败', '认证服务未签发有效凭证']
  ];
  rejectSources.forEach((item, index) => {
    const y = 2.12 + index * 0.62;
    slide.addShape(S.roundRect, {
      x: 3.97, y, w: 4.58, h: 0.54,
      rectRadius: 0.035,
      fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
    });
    slide.addText(item[0], {
      x: 4.18, y: y + 0.08, w: 2.0, h: 0.18,
      fontSize: 8.2, bold: true, color: C.red, margin: 0
    });
    slide.addText(item[1], {
      x: 4.18, y: y + 0.28, w: 4.16, h: 0.18,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
  });
  slide.addShape(S.roundRect, {
    x: 3.97, y: 4.62, w: 4.58, h: 0.74,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('status = REJECTED,   result.reason = "denied_or_not_authorized"', {
    x: 4.18, y: 4.76, w: 4.16, h: 0.2,
    fontFace: 'Consolas', fontSize: 7.6, bold: true, color: C.red, margin: 0
  });
  slide.addText('四类原因对外统一表述，避免把内部判定细节泄露给用户。', {
    x: 4.18, y: 5.0, w: 4.16, h: 0.24,
    fontSize: 7.4, color: C.red, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 3.97, y: 5.5, w: 4.58, h: 0.98,
    rectRadius: 0.04,
    fill: { color: 'E8F3EC' }, line: { color: C.green, width: 1 }
  });
  slide.addText('执行节点还差什么才算生产级', {
    x: 4.18, y: 5.64, w: 4.16, h: 0.18,
    fontSize: 8.4, bold: true, color: C.green, margin: 0
  });
  slide.addText('数据库事务、唯一幂等键、限额与账户状态复检、授权有效期；本示例只计算返回值，不会真正持久化扣款。', {
    x: 4.18, y: 5.86, w: 4.16, h: 0.52,
    fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
  });

  // 右栏：result 与 response 的分工。
  slide.addText('3  result 与 response 分开', {
    x: 8.82, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 8.82, y: 2.12, w: 3.84, h: 1.5,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 8.82, y: 2.12, w: 3.84, h: 0.4,
    fill: { color: C.navy2 }, line: { color: C.navy2 }
  });
  slide.addText('result：结构化业务事实', {
    x: 9.04, y: 2.24, w: 3.0, h: 0.18,
    fontSize: 8.8, bold: true, color: C.white, margin: 0
  });
  slide.addText('{\n  "operation": "TRANSFER",\n  "recipient": "张伟",\n  "amount": 300.0,\n  "currency": "CNY",\n  "remaining_balance": 4700.0\n}', {
    x: 9.04, y: 2.6, w: 3.4, h: 0.96,
    fontFace: 'Consolas', fontSize: 7.2, color: C.ink,
    margin: 0, valign: 'top', fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 8.82, y: 3.76, w: 3.84, h: 1.5,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 8.82, y: 3.76, w: 3.84, h: 0.4,
    fill: { color: C.teal }, line: { color: C.teal }
  });
  slide.addText('response：给用户的自然语言', {
    x: 9.04, y: 3.88, w: 3.2, h: 0.18,
    fontSize: 8.8, bold: true, color: C.white, margin: 0
  });
  slide.addText('已向 张伟 转账 300.00 CNY，\n剩余余额 4700.00 CNY。', {
    x: 9.04, y: 4.24, w: 3.4, h: 0.5,
    fontSize: 8.2, color: C.ink, margin: 0
  });
  slide.addText('回复由 compose_response 依据 result 生成，只在 status=COMPLETED 时才表述成功。', {
    x: 9.04, y: 4.76, w: 3.4, h: 0.4,
    fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 8.82, y: 5.42, w: 3.84, h: 1.06,
    rectRadius: 0.04,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('为什么必须分开', {
    x: 9.04, y: 5.56, w: 2.6, h: 0.18,
    fontSize: 8.8, bold: true, color: C.purple, margin: 0
  });
  slide.addText('事实与措辞分离，模型就无法"顺手"编造余额或改写状态；前端也能用同一份事实渲染业务卡片，而不必解析自然语言。', {
    x: 9.04, y: 5.8, w: 3.4, h: 0.62,
    fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.66, w: 11.99, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('即使已经走到执行节点，授权也必须来自服务端验证结果；越靠近真实状态，复检越不能省', {
    x: 0.93, y: 6.75, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.red, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.14, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('14', {
    x: 12.55, y: 7.12, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第十五页：Checkpoint、thread_id 与三种结束语义
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('CHECKPOINT', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('Checkpoint 与 thread_id：一次运行到底停在了哪里', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('暂停和恢复能成立，全靠 Checkpoint 保存了 State 加执行位置；而 thread_id 是找回它的钥匙。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：Checkpoint 的组成。
  slide.addText('1  Checkpoint 里存了什么', {
    x: 0.62, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 0.62, y: 2.12, w: 3.17, h: 1.5,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 0.62, y: 2.12, w: 3.17, h: 0.4,
    fill: { color: C.navy2 }, line: { color: C.navy2 }
  });
  slide.addText('Checkpoint = State + 执行位置', {
    x: 0.84, y: 2.24, w: 2.8, h: 0.18,
    fontSize: 8.6, bold: true, color: C.white, margin: 0, fit: 'shrink'
  });
  slide.addText('compile(checkpointer=InMemorySaver())', {
    x: 0.84, y: 2.62, w: 2.78, h: 0.2,
    fontFace: 'Consolas', fontSize: 7.0, bold: true, color: C.navy2, margin: 0, fit: 'shrink'
  });
  slide.addText('保存依赖同一个 compiled graph 与 checkpointer 实例；重新 build_graph 会得到一个新的空 saver，即使进程没退出。', {
    x: 0.84, y: 2.88, w: 2.78, h: 0.62,
    fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 3.76, w: 3.17, h: 1.5,
    rectRadius: 0.04,
    fill: { color: 'E5F2F0' }, line: { color: C.teal, width: 1 }
  });
  slide.addText('thread_id 不在 State 里', {
    x: 0.84, y: 3.92, w: 2.7, h: 0.2,
    fontSize: 8.8, bold: true, color: C.teal, margin: 0
  });
  slide.addText('它是 config 里的查询键：config = {"configurable": {"thread_id": ...}}。21 个 State 字段里没有它。', {
    x: 0.84, y: 4.16, w: 2.78, h: 0.62,
    fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
  });
  slide.addText('thread_id 是会话标签，不等于认证用户身份。', {
    x: 0.84, y: 4.82, w: 2.78, h: 0.32,
    fontSize: 7.4, bold: true, color: C.teal, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 5.4, w: 3.17, h: 1.08,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1.1 }
  });
  slide.addText('Checkpoint 不是核心账本', {
    x: 0.84, y: 5.54, w: 2.7, h: 0.2,
    fontSize: 8.8, bold: true, color: C.red, margin: 0
  });
  slide.addText('它只是工作流快照。恢复流程时仍要向业务系统重新确认交易状态，避免把快照当成余额或成交流水。', {
    x: 0.84, y: 5.78, w: 2.78, h: 0.6,
    fontSize: 7.2, color: C.red, margin: 0, fit: 'shrink'
  });

  // 中栏：三种结束语义对比。
  slide.addText('2  三种"结束"完全不是一回事', {
    x: 3.97, y: 1.72, w: 3.6, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const endTypes = [
    {
      name: 'ask_clarification → END', color: C.amber, fill: 'FBF1D8',
      lines: ['本轮运行结束，State 留在 Checkpoint', '下一轮是同 thread 的新 invoke，从 START 重来', '不是 resume：旧 State 先合并，再注入新可信上下文']
    },
    {
      name: 'interrupt → 暂停', color: C.red, fill: 'F9E7E5',
      lines: ['运行没有结束，只是停在中途', '用同 thread + Command(resume=...) 继续', '节点从头重跑，所以中断前不能有副作用']
    },
    {
      name: '执行完 → END', color: C.green, fill: 'E8F3EC',
      lines: ['工作流正常走完，compose_response 已写入回复', '再发消息就是同一 thread 的下一轮', 'State 会先合并旧值，API 必须每轮重新注入可信字段']
    }
  ];
  endTypes.forEach((item, index) => {
    const y = 2.12 + index * 1.52;
    slide.addShape(S.roundRect, {
      x: 3.97, y, w: 4.58, h: 1.38,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.name, {
      x: 4.18, y: y + 0.12, w: 4.16, h: 0.2,
      fontFace: 'Consolas', fontSize: 8.8, bold: true, color: item.color, margin: 0, fit: 'shrink'
    });
    slide.addText(item.lines.map((line) => '• ' + line).join('\n'), {
      x: 4.18, y: y + 0.38, w: 4.16, h: 0.9,
      fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 右栏：从这张图能学到什么。
  slide.addText('3  这一节要记住的机制', {
    x: 8.82, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const mechanisms = [
    ['State 合并', '节点只返回变更字段，LangGraph 负责合并进旧 State'],
    ['Checkpoint', '保存 State 与执行位置，使流程可暂停、可恢复'],
    ['thread_id', 'config 中的查询键，决定去哪个 Checkpoint 恢复'],
    ['interrupt', '在节点内部暂停，把展示载荷交给外部界面'],
    ['resume', '同 thread 提交决定，节点重跑并得到该决定'],
    ['END 的语义', '澄清结束、正常完成、中断暂停三者互不相同'],
    ['持久化替换点', '生产环境换 PostgreSQL Checkpointer，内存版退出即丢']
  ];
  mechanisms.forEach((item, index) => {
    const y = 2.12 + index * 0.63;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.84, h: 0.55,
      rectRadius: 0.035,
      fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
    });
    slide.addText(item[0], {
      x: 9.04, y: y + 0.06, w: 1.3, h: 0.18,
      fontSize: 8.0, bold: true, color: C.navy2, margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 9.04, y: y + 0.26, w: 3.4, h: 0.22,
      fontSize: 7.0, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.62, w: 11.99, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('同一个 thread 的下一轮会先合并旧 State；API 必须每轮重新校验并注入可信上下文，禁止跨用户复用 thread', {
    x: 0.93, y: 6.71, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('15', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第十六页：全流程总览与 LangGraph 机制对照
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('FULL PICTURE', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('全流程总览：14 个节点、条件边与三处结束', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('从 load_context 到 compose_response 的全部路径，以及这套示例用到的 LangGraph 机制清单。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 顶部：主链路节点带。
  slide.addShape(S.roundRect, {
    x: 0.62, y: 1.66, w: 12.11, h: 1.06,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  const chain = [
    ['START', C.navy2], ['load_context', C.navy2], ['understand_intent', C.purple],
    ['resolve_entities', C.purple], ['create_plan', C.navy2], ['validate_plan', C.navy2],
    ['security_policy', C.amber], ['interrupt / execute', C.red], ['compose_response', C.teal], ['END', C.navy2]
  ];
  chain.forEach((item, index) => {
    const x = 0.78 + index * 1.2;
    slide.addShape(S.roundRect, {
      x, y: 1.82, w: 1.06, h: 0.4,
      rectRadius: 0.03,
      fill: { color: item[1] }, line: { color: item[1] }
    });
    slide.addText(item[0], {
      x: x + 0.03, y: 1.95, w: 1.0, h: 0.16,
      fontFace: 'Consolas', fontSize: 6.8, bold: true, color: C.white,
      align: 'center', margin: 0, fit: 'shrink'
    });
    if (index < chain.length - 1) {
      slide.addShape(S.line, {
        x: x + 1.06, y: 2.02, w: 0.14, h: 0,
        line: { color: '98A5AF', width: 1, endArrowType: 'triangle' }
      });
    }
  });
  slide.addText('分支离开主链路：resolve_entities → ask_clarification → END　|　validate_plan → reject_plan　|　security_policy → reject_operation　|　load_context → compose_response', {
    x: 0.82, y: 2.36, w: 11.7, h: 0.28,
    fontSize: 7.6, color: C.muted, margin: 0, fit: 'shrink'
  });

  // 左下：LangGraph 机制对照表。
  slide.addText('1  这套示例用到的 LangGraph 机制', {
    x: 0.62, y: 2.86, w: 4.0, h: 0.28,
    fontSize: 13, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 0.62, y: 3.22, w: 6.15, h: 3.24,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  const langgraphTable = [
    ['StateGraph + TypedDict', '声明 21 个字段与图结构'],
    ['add_node / add_edge', '注册 14 个节点与固定顺序'],
    ['add_conditional_edges', '四处条件边共 9 个分支'],
    ['路由函数', '只返回路径名，不修改 State'],
    ['interrupt', '节点内暂停，交出展示载荷'],
    ['Command(resume=...)', '同 thread 恢复，节点重跑'],
    ['InMemorySaver', 'Checkpoint 保存 State 与位置'],
    ['total=False 的 TypedDict', '字段分组可选，靠节点逐步补全']
  ];
  langgraphTable.forEach((item, index) => {
    const y = 3.38 + index * 0.38;
    if (index > 0) {
      slide.addShape(S.line, {
        x: 0.86, y: y - 0.04, w: 5.67, h: 0,
        line: { color: 'EDF1F4', width: 0.8 }
      });
    }
    slide.addText(item[0], {
      x: 0.86, y: y + 0.03, w: 2.3, h: 0.16,
      fontFace: 'Consolas', fontSize: 7.4, bold: true, color: C.navy2, margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 3.24, y: y + 0.03, w: 3.3, h: 0.16,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  // 右下：示例边界与生产差距。
  slide.addText('2  示例的边界', {
    x: 7.04, y: 2.86, w: 2.6, h: 0.28,
    fontSize: 13, bold: true, color: C.ink, margin: 0
  });
  const limits = [
    ['模型', '规则与正则模拟，未接真实模型，也没有结构化输出约束'],
    ['身份', '没有 FastAPI 认证；教学版本直接把可信上下文当作输入'],
    ['金额', 'float 只用于缩短示例；真实金额用 Decimal 或整数分'],
    ['存储', 'InMemorySaver 与内存常量；无数据库事务与持久化'],
    ['幂等', '示例未实现幂等键，重复执行不会重复扣款只是因为没真的扣款'],
    ['认证', 'demo-otp-ok 是固定字符串，不是生产认证'],
    ['多轮', '尚未实现跨轮槽位合并：只回复“300 元”不会与上一轮自动合并'],
    ['非银行请求', '当前统一归 UNKNOWN 后拒绝；寒暄与范围外分流留待正式版']
  ];
  limits.forEach((item, index) => {
    const y = 3.22 + index * 0.405;
    slide.addShape(S.roundRect, {
      x: 7.04, y, w: 5.69, h: 0.35,
      rectRadius: 0.03,
      fill: { color: index % 2 === 0 ? 'F6F8FA' : 'FFFFFF' },
      line: { color: 'E1E6EA', width: 0.8 }
    });
    slide.addText(item[0], {
      x: 7.22, y: y + 0.08, w: 0.95, h: 0.18,
      fontSize: 7.4, bold: true, color: C.red, margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 8.22, y: y + 0.07, w: 4.34, h: 0.2,
      fontSize: 7.0, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.62, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'E8F3EC' }, line: { color: C.green, width: 1 }
  });
  slide.addText('源码解读到此结束：LangGraph 负责流程与状态，Python 负责判定与执行，模型只负责理解与表达', {
    x: 0.93, y: 6.71, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.green, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('16', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第十七页：账单分析场景需要的工具
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('SCENARIO TOOLS · BILLS', {
    x: 0.62, y: 0.42, w: 3.6, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('账单分析：工具只负责算，模型只负责解释', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 1.24, w: 12.11, h: 0.32,
    rectRadius: 0.035,
    fill: { color: 'E5F2F0' }, line: { color: C.teal, width: 1 }
  });
  slide.addText('复杂度 2/5　　|　　[设计目标，待实现]　教学源码未包含本场景任何工具', {
    x: 0.93, y: 1.33, w: 11.5, h: 0.15,
    fontSize: 8.2, bold: true, color: C.teal, align: 'center', margin: 0
  });
  slide.addText('聚合、分类、异常检测都是确定性的 SQL 与 Python 计算；模型没有算术能力，也不该被用来算钱。', {
    x: 0.62, y: 1.63, w: 11.8, h: 0.24,
    fontSize: 10, color: C.muted, margin: 0
  });

  // 左栏：工具清单。
  slide.addText('1  需要哪些工具', {
    x: 0.62, y: 2.02, w: 2.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const billTools = [
    {
      name: 'list_transactions', color: C.navy2, fill: 'E9F1F7',
      args: 'account_id, from_date, to_date',
      desc: '按时间范围取明细。仍是查询类工具，不修改任何状态。'
    },
    {
      name: 'summarize_by_category', color: C.purple, fill: 'EFE9F6',
      args: 'account_id, period, group_by',
      desc: '在数据库侧做聚合与分类，返回结构化金额，不做自然语言描述。'
    },
    {
      name: 'detect_anomalies', color: C.amber, fill: 'FBF1D8',
      args: 'account_id, period, rules',
      desc: '用确定性规则找出重复扣款、异常大额等可疑交易，返回证据。'
    }
  ];
  billTools.forEach((item, index) => {
    const y = 2.4 + index * 1.28;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 3.9, h: 1.16,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.name, {
      x: 0.84, y: y + 0.12, w: 3.5, h: 0.2,
      fontFace: 'Consolas', fontSize: 9.4, bold: true, color: item.color, margin: 0, fit: 'shrink'
    });
    slide.addText(item.args, {
      x: 0.84, y: y + 0.36, w: 3.5, h: 0.16,
      fontFace: 'Consolas', fontSize: 7.0, color: C.muted, margin: 0, fit: 'shrink'
    });
    slide.addText(item.desc, {
      x: 0.84, y: y + 0.58, w: 3.5, h: 0.48,
      fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：结构化结果与证据。
  slide.addText('2  工具返回什么', {
    x: 4.82, y: 2.02, w: 2.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 4.82, y: 2.4, w: 4.12, h: 2.52,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 4.82, y: 2.4, w: 4.12, h: 0.4,
    fill: { color: C.navy2 }, line: { color: C.navy2 }
  });
  slide.addText('detect_anomalies 的返回', {
    x: 5.04, y: 2.52, w: 3.7, h: 0.18,
    fontSize: 8.6, bold: true, color: C.white, margin: 0
  });
  slide.addText('{\n  "period": "2026-09",\n  "total": 8420.50,\n  "by_category": {\n    "餐饮": 2310.00,\n    "订阅": 128.00\n  },\n  "anomalies": [\n    {"type": "duplicate_charge",\n     "amount": 25.00, "count": 2}\n  ],\n  "evidence": ["txn-8841", "txn-8842"]\n}', {
    x: 5.04, y: 2.88, w: 3.7, h: 1.96,
    fontFace: 'Consolas', fontSize: 7.0, color: C.ink,
    margin: 0, valign: 'top', fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 4.82, y: 5.04, w: 4.12, h: 1.44,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1.1 }
  });
  slide.addText('Evidence 字段是这一页的重点', {
    x: 5.04, y: 5.18, w: 3.7, h: 0.2,
    fontSize: 9.0, bold: true, color: C.red, margin: 0
  });
  slide.addText('每条结论都必须带回原始交易 ID。模型只能引用这些证据来解释，不能凭印象说"你最近花得比较多"。', {
    x: 5.04, y: 5.44, w: 3.7, h: 0.62,
    fontSize: 7.6, color: C.red, margin: 0, fit: 'shrink'
  });
  slide.addText('异常真值标签仅供测试比对，不能出现在返回里，否则等于把答案交给模型。', {
    x: 5.04, y: 6.05, w: 3.7, h: 0.34,
    fontSize: 7.4, bold: true, color: C.red, margin: 0, fit: 'shrink'
  });

  // 右栏：一次调用的顺序。
  slide.addText('3  调用顺序', {
    x: 9.16, y: 2.02, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const billFlow = [
    ['1', '锁定账户与周期', 'account_id 由服务端验证归属，period 由用户选择'],
    ['2', '取明细或直接聚合', '按需调用 list_transactions / summarize_by_category'],
    ['3', '跑异常规则', 'detect_anomalies 用确定性规则，不用相似度猜测'],
    ['4', '模型组织解释', '只依据返回的结构化事实与 evidence 生成说明']
  ];
  billFlow.forEach((item, index) => {
    const y = 2.4 + index * 1.02;
    slide.addShape(S.roundRect, {
      x: 9.16, y, w: 3.57, h: 0.9,
      rectRadius: 0.04,
      fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
    });
    slide.addShape(S.ellipse, {
      x: 9.36, y: y + 0.14, w: 0.3, h: 0.3,
      fill: { color: C.teal }, line: { color: C.teal }
    });
    slide.addText(item[0], {
      x: 9.36, y: y + 0.22, w: 0.3, h: 0.12,
      fontSize: 6.8, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 9.78, y: y + 0.12, w: 2.8, h: 0.18,
      fontSize: 8.6, bold: true, color: C.ink, margin: 0
    });
    slide.addText(item[2], {
      x: 9.78, y: y + 0.34, w: 2.8, h: 0.44,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
    if (index < billFlow.length - 1) {
      slide.addShape(S.line, {
        x: 9.51, y: y + 0.3, w: 0, h: 0.72,
        line: { color: '98A5AF', width: 1, endArrowType: 'triangle' }
      });
    }
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.6, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('账单场景没有写操作：全部是绿色查询，不触发确认、强认证与幂等要求', {
    x: 0.93, y: 6.69, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('17', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第十八页：订阅与代扣管理场景需要的工具
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('SCENARIO TOOLS · SUBSCRIPTIONS', {
    x: 0.62, y: 0.42, w: 4.0, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('订阅与代扣：取消申请不等于取消成功', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 1.24, w: 12.11, h: 0.32,
    rectRadius: 0.035,
    fill: { color: 'E5F2F0' }, line: { color: C.teal, width: 1 }
  });
  slide.addText('复杂度 2.5/5　　|　　[设计目标，待实现]　教学源码未包含本场景任何工具', {
    x: 0.93, y: 1.33, w: 11.5, h: 0.15,
    fontSize: 8.2, bold: true, color: C.teal, align: 'center', margin: 0
  });
  slide.addText('代扣协议是三方关系：用户、银行、商户。银行能停扣款，但不能替商户关闭服务。', {
    x: 0.62, y: 1.63, w: 11.8, h: 0.24,
    fontSize: 10, color: C.muted, margin: 0
  });

  // 左栏：工具清单。
  slide.addText('1  需要哪些工具', {
    x: 0.62, y: 2.02, w: 2.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const subTools = [
    {
      name: 'list_recurring_charges', color: C.navy2, fill: 'E9F1F7',
      args: 'account_id, status',
      desc: '识别周期扣款：同商户、近似金额、固定间隔。返回协议与最近扣款记录。'
    },
    {
      name: 'verify_mandate', color: C.purple, fill: 'EFE9F6',
      args: 'mandate_id',
      desc: '核实代扣协议是否真实有效：签约时间、限额、商户主体、是否已终止。'
    },
    {
      name: 'request_cancellation', color: C.amber, fill: 'FBF1D8',
      args: 'mandate_id, reason',
      desc: '提交停扣申请。这是写操作，会产生申请单号并进入处理中状态。'
    },
    {
      name: 'get_cancellation_status', color: C.green, fill: 'E8F3EC',
      args: 'cancellation_id',
      desc: '查询处理结果。只有商户确认后才是真正终止。'
    }
  ];
  subTools.forEach((item, index) => {
    const y = 2.4 + index * 1.0;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.32, h: 0.9,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.name, {
      x: 0.82, y: y + 0.1, w: 3.94, h: 0.18,
      fontFace: 'Consolas', fontSize: 8.6, bold: true, color: item.color, margin: 0, fit: 'shrink'
    });
    slide.addText(item.args, {
      x: 0.82, y: y + 0.3, w: 3.94, h: 0.14,
      fontFace: 'Consolas', fontSize: 6.8, color: C.muted, margin: 0, fit: 'shrink'
    });
    slide.addText(item.desc, {
      x: 0.82, y: y + 0.47, w: 3.94, h: 0.38,
      fontSize: 7.3, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：状态推进。
  slide.addText('2  状态是这样推进的', {
    x: 5.24, y: 2.02, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const subStates = [
    ['申请已提交', 'PENDING', 'request_cancellation 返回申请单号', C.amber, 'FBF1D8'],
    ['银行已受理', 'ACCEPTED', '扣款通道收到停扣指令', C.navy2, 'E9F1F7'],
    ['商户已确认', 'CONFIRMED', '商户回执到达，服务侧终止', C.green, 'E8F3EC'],
    ['已终止 / 被拒绝', 'CANCELLED / REJECTED', '终态；被拒绝要说明原因', C.red, 'F9E7E5']
  ];
  subStates.forEach((item, index) => {
    const y = 2.4 + index * 1.0;
    slide.addShape(S.roundRect, {
      x: 5.24, y, w: 3.7, h: 0.88,
      rectRadius: 0.04,
      fill: { color: item[4] }, line: { color: item[3], width: 1 }
    });
    slide.addText(item[0], {
      x: 5.46, y: y + 0.1, w: 3.3, h: 0.18,
      fontSize: 8.8, bold: true, color: C.ink, margin: 0
    });
    slide.addText(item[1], {
      x: 5.46, y: y + 0.3, w: 3.3, h: 0.16,
      fontFace: 'Consolas', fontSize: 7.4, bold: true, color: item[3], margin: 0, fit: 'shrink'
    });
    slide.addText(item[2], {
      x: 5.46, y: y + 0.5, w: 3.3, h: 0.3,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
    if (index < subStates.length - 1) {
      slide.addShape(S.line, {
        x: 7.09, y: y + 0.88, w: 0, h: 0.12,
        line: { color: '98A5AF', width: 1, endArrowType: 'triangle' }
      });
    }
  });

  // 右栏：措辞边界与关键规则。
  slide.addText('3  必须守住的三条', {
    x: 9.16, y: 2.02, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const subRules = [
    ['① 区分申请与成功', '提交停扣后只能说"已提交申请"，不能承诺"已退订"。用户最容易在这里被误导。'],
    ['② 取消前先核实协议', '必须 verify_mandate：协议可能早已终止，或根本不是用户以为的那个商户。'],
    ['③ 剩余扣款要交代', '本期是否仍会扣、下期何时生效，都要明确说明，不能含糊。']
  ];
  subRules.forEach((item, index) => {
    const y = 2.4 + index * 1.34;
    slide.addShape(S.roundRect, {
      x: 9.16, y, w: 3.57, h: 1.22,
      rectRadius: 0.04,
      fill: { color: 'FFFFFF' }, line: { color: index === 0 ? C.amber : 'C8D4DE', width: 1 }
    });
    slide.addText(item[0], {
      x: 9.38, y: y + 0.12, w: 3.15, h: 0.2,
      fontSize: 9.0, bold: true, color: index === 0 ? C.amber : C.navy2, margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 9.38, y: y + 0.38, w: 3.15, h: 0.74,
      fontSize: 7.6, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.6, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('停扣是银行侧动作，关闭服务是商户侧动作；两者之间有延迟，措辞不能替商户承诺', {
    x: 0.93, y: 6.69, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.red, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('18', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第十九页：卡片管理场景需要的工具
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('SCENARIO TOOLS · CARDS', {
    x: 0.62, y: 0.42, w: 3.6, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('卡片管理：状态机决定了哪些操作不可逆', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 1.24, w: 12.11, h: 0.32,
    rectRadius: 0.035,
    fill: { color: 'E5F2F0' }, line: { color: C.teal, width: 1 }
  });
  slide.addText('复杂度 3/5　　|　　[设计目标，待实现]　教学源码未包含本场景任何工具', {
    x: 0.93, y: 1.33, w: 11.5, h: 0.15,
    fontSize: 8.2, bold: true, color: C.teal, align: 'center', margin: 0
  });
  slide.addText('卡片的可用操作完全取决于它当前处于哪个状态；状态不对，工具必须直接拒绝。', {
    x: 0.62, y: 1.63, w: 11.8, h: 0.24,
    fontSize: 10, color: C.muted, margin: 0
  });

  // 左栏：工具清单。
  slide.addText('1  需要哪些工具', {
    x: 0.62, y: 2.02, w: 2.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const cardTools = [
    ['get_card_status', '查状态、额度、是否在途', C.navy2, 'E9F1F7'],
    ['freeze_card', '冻结，可解冻；不改变卡号', C.teal, 'E5F2F0'],
    ['report_lost', '挂失，不可逆，必然补卡', C.red, 'F9E7E5'],
    ['apply_limit_change', '调整限额，需审核，异步生效', C.amber, 'FBF1D8']
  ];
  cardTools.forEach((item, index) => {
    const col = index % 2;
    const row = Math.floor(index / 2);
    const x = 0.62 + col * 2.28;
    const y = 2.4 + row * 1.5;
    slide.addShape(S.roundRect, {
      x, y, w: 2.14, h: 1.36,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: x + 0.18, y: y + 0.14, w: 1.8, h: 0.34,
      fontFace: 'Consolas', fontSize: 8.4, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: x + 0.18, y: y + 0.56, w: 1.8, h: 0.66,
      fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 5.5, w: 4.42, h: 1.04,
    rectRadius: 0.04,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('额度工具为什么必须异步', {
    x: 0.84, y: 5.64, w: 4.0, h: 0.18,
    fontSize: 8.6, bold: true, color: C.purple, margin: 0
  });
  slide.addText('提额涉及风控审核，不可能即时生效。工具只返回"申请已受理"，最终结果要靠查询确认。', {
    x: 0.84, y: 5.88, w: 4.0, h: 0.54,
    fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
  });

  // 中栏：状态机。
  slide.addText('2  卡片状态迁移', {
    x: 5.24, y: 2.02, w: 2.6, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 5.24, y: 2.4, w: 3.7, h: 4.14,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  const cardStates = [
    ['NORMAL', '正常可用', C.teal, 2.6],
    ['FROZEN', '已冻结，可解冻回正常', C.navy2, 3.44],
    ['LOST', '已挂失，不可逆', C.red, 4.28],
    ['CLOSED', '已销户，终态', '8A5A55', 5.12]
  ];
  cardStates.forEach((item) => {
    slide.addShape(S.roundRect, {
      x: 5.48, y: item[3], w: 3.22, h: 0.62,
      rectRadius: 0.035,
      fill: { color: 'F6F8FA' }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 5.68, y: item[3] + 0.1, w: 1.2, h: 0.18,
      fontFace: 'Consolas', fontSize: 8.8, bold: true, color: item[2], margin: 0
    });
    slide.addText(item[1], {
      x: 6.92, y: item[3] + 0.12, w: 1.7, h: 0.36,
      fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
    });
  });
  slide.addText('NORMAL ⇄ FROZEN：双向可逆\nNORMAL / FROZEN → LOST：单向不可逆', {
    x: 5.48, y: 5.84, w: 3.22, h: 0.34,
    fontSize: 7.2, bold: true, color: C.navy, margin: 0, fit: 'shrink'
  });
  slide.addText('LOST → NORMAL 不存在：挂失只能补新卡', {
    x: 5.48, y: 6.22, w: 3.22, h: 0.18,
    fontSize: 7.2, bold: true, color: C.red, margin: 0, fit: 'shrink'
  });

  // 右栏：调用规则。
  slide.addText('3  每个工具的前置条件', {
    x: 9.16, y: 2.02, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const cardRules = [
    ['freeze_card', '仅 NORMAL 可冻结；FROZEN 重复冻结要幂等返回，不报错'],
    ['report_lost', 'NORMAL / FROZEN 均可挂失；已 LOST 再挂失直接拒绝'],
    ['apply_limit_change', 'LOST 与 CLOSED 均不可申请；有在途申请时不允许重复提交'],
    ['所有写操作', '都要校验账户归属：卡片必须属于当前登录用户的账户']
  ];
  cardRules.forEach((item, index) => {
    const y = 2.4 + index * 1.04;
    slide.addShape(S.roundRect, {
      x: 9.16, y, w: 3.57, h: 0.94,
      rectRadius: 0.04,
      fill: { color: index === 3 ? 'F9E7E5' : 'FFFFFF' },
      line: { color: index === 3 ? 'E7B8B4' : 'C8D4DE', width: 1 }
    });
    slide.addText(item[0], {
      x: 9.38, y: y + 0.11, w: 3.15, h: 0.18,
      fontFace: 'Consolas', fontSize: 8.4, bold: true, color: index === 3 ? C.red : C.navy2, margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 9.38, y: y + 0.34, w: 3.15, h: 0.52,
      fontSize: 7.3, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.6, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('状态机是确定性代码，模型既不能跳过前置校验，也不能把挂失说成可以随时恢复', {
    x: 0.93, y: 6.69, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('19', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第二十页：智能转账的工具矩阵（复用交叉引用）
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('SCENARIO TOOLS · TRANSFER', {
    x: 0.62, y: 0.42, w: 4.0, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('智能转账：工具的授权级别，才是安全边界的落点', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 1.24, w: 12.11, h: 0.32,
    rectRadius: 0.035,
    fill: { color: 'E8F3EC' }, line: { color: C.green, width: 1 }
  });
  slide.addText('复杂度 4/5　　|　　[源码已实现]　完整流程见第 8–16 页：understand_intent → resolve_entities → 计划 → 风险 → 中断 → 执行', {
    x: 0.93, y: 1.33, w: 11.5, h: 0.15,
    fontSize: 8.2, bold: true, color: C.green, align: 'center', margin: 0
  });
  slide.addText('同一个功能，可以拆成"模型可用"和"模型不可用"两套工具；差别只在授权级别。', {
    x: 0.62, y: 1.63, w: 11.8, h: 0.24,
    fontSize: 10, color: C.muted, margin: 0
  });

  // 左栏：模型可用的工具。
  slide.addText('1  模型可以调用的工具', {
    x: 0.62, y: 2.02, w: 3.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addText('全部为查询或"准备"类，不改变资金状态', {
    x: 0.62, y: 2.3, w: 4.6, h: 0.18,
    fontSize: 8.0, italic: true, color: C.muted, margin: 0
  });
  const allowedTools = [
    ['get_balance', '查询可用余额', '只读，绿色等级，可直接执行'],
    ['get_transfer_limit', '查询转账限额与当日已用额度', '只读，绿色等级'],
    ['prepare_transfer', '创建待确认的转账草稿', '返回 PENDING_CONFIRMATION，不扣款'],
    ['get_transfer_status', '查询某笔转账的当前状态', '只读，用于断线后核对结果']
  ];
  allowedTools.forEach((item, index) => {
    const y = 2.5 + index * 1.06;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 0.96,
      rectRadius: 0.04,
      fill: { color: 'E8F3EC' }, line: { color: C.green, width: 1 }
    });
    slide.addText(item[0], {
      x: 0.84, y: y + 0.11, w: 2.4, h: 0.18,
      fontFace: 'Consolas', fontSize: 9.0, bold: true, color: C.green, margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 0.84, y: y + 0.33, w: 4.0, h: 0.18,
      fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
    });
    slide.addText(item[2], {
      x: 0.84, y: y + 0.53, w: 4.0, h: 0.36,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：模型不可用的工具。
  slide.addText('2  模型永远拿不到的工具', {
    x: 5.24, y: 2.02, w: 3.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addText('不给工具，比在提示词里禁止更可靠', {
    x: 5.24, y: 2.3, w: 3.7, h: 0.18,
    fontSize: 8.0, italic: true, color: C.red, margin: 0
  });
  const forbiddenTools = [
    {
      name: 'approve_transfer', color: C.amber, fill: 'FBF1D8',
      desc: '批准必须来自用户确认或强认证，不能由模型或普通函数参数触发。'
    },
    {
      name: 'execute_transfer', color: C.red, fill: 'F9E7E5',
      desc: '执行由可信后端完成；图里的 execute_operation 是程序节点，不是可调用工具。'
    },
    {
      name: '任意 SQL / 密钥读取', color: C.red, fill: 'F9E7E5',
      desc: '不提供数据库直连与凭据获取能力，避免绕过业务规则与审计。'
    }
  ];
  forbiddenTools.forEach((item, index) => {
    const y = 2.5 + index * 1.28;
    slide.addShape(S.roundRect, {
      x: 5.24, y, w: 3.7, h: 1.16,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1.1 }
    });
    slide.addText(item.name, {
      x: 5.46, y: y + 0.12, w: 3.3, h: 0.2,
      fontFace: 'Consolas', fontSize: 9.0, bold: true, color: item.color, margin: 0, fit: 'shrink'
    });
    slide.addText(item.desc, {
      x: 5.46, y: y + 0.38, w: 3.3, h: 0.7,
      fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 右栏：三阶段流程。
  slide.addText('3  准备 → 授权 → 执行', {
    x: 9.16, y: 2.02, w: 3.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const transferPhases = [
    {
      title: '准备', color: C.purple, fill: 'EFE9F6',
      lines: ['模型提议 prepare_transfer', '服务端校验收款人与金额格式', '创建 PENDING_CONFIRMATION 草稿']
    },
    {
      title: '授权', color: C.amber, fill: 'FBF1D8',
      lines: ['黄色：独立界面确认', '红色：强认证服务', '校验挑战与操作哈希一致']
    },
    {
      title: '执行', color: C.green, fill: 'E8F3EC',
      lines: ['再次复检授权、余额、限额', '数据库事务 + 幂等键', '状态改为 COMPLETED']
    }
  ];
  transferPhases.forEach((item, index) => {
    const y = 2.4 + index * 1.36;
    slide.addShape(S.roundRect, {
      x: 9.16, y, w: 3.57, h: 1.24,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 9.38, y: y + 0.12, w: 2.0, h: 0.2,
      fontSize: 9.6, bold: true, color: item.color, margin: 0
    });
    slide.addText(item.lines.map((line) => '· ' + line).join('\n'), {
      x: 9.38, y: y + 0.38, w: 3.15, h: 0.76,
      fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
    });
    if (index < transferPhases.length - 1) {
      slide.addShape(S.line, {
        x: 10.94, y: y + 1.24, w: 0, h: 0.12,
        line: { color: '98A5AF', width: 1, endArrowType: 'triangle' }
      });
    }
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.6, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('安全边界最终体现为工具清单：模型能调用哪些工具，就是它真正的能力上限', {
    x: 0.93, y: 6.69, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('20', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第二十一页：理财场景（上）风险测评与适当性
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('SCENARIO TOOLS · RISK PROFILE', {
    x: 0.62, y: 0.42, w: 4.4, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('理财（上）：先有有效风险画像，才谈得上推荐', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 1.24, w: 12.11, h: 0.32,
    rectRadius: 0.035,
    fill: { color: 'E5F2F0' }, line: { color: C.teal, width: 1 }
  });
  slide.addText('复杂度 4.5/5　　|　　[设计目标，待实现]　教学源码未包含本场景任何工具；本节分两页，本页讲测评', {
    x: 0.93, y: 1.33, w: 11.5, h: 0.15,
    fontSize: 8.2, bold: true, color: C.teal, align: 'center', margin: 0
  });
  slide.addText('适当性是监管硬要求：画像无效就不能推荐，信息不足只能给客观介绍。', {
    x: 0.62, y: 1.63, w: 11.8, h: 0.24,
    fontSize: 10, color: C.muted, margin: 0
  });

  // 左栏：工具与收集字段。
  slide.addText('1  工具与收集的信息', {
    x: 0.62, y: 2.02, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const profileTools = [
    ['get_risk_profile', '查有效画像与到期时间', C.green, 'E8F3EC'],
    ['assess_risk_profile', '按确定性规则生成画像', C.purple, 'EFE9F6'],
    ['save_risk_profile', '保存问卷与结果', C.navy2, 'E9F1F7']
  ];
  profileTools.forEach((item, index) => {
    const y = 2.4 + index * 0.66;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 0.58,
      rectRadius: 0.035,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 0.84, y: y + 0.09, w: 2.5, h: 0.18,
      fontFace: 'Consolas', fontSize: 8.8, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 0.84, y: y + 0.31, w: 4.0, h: 0.18,
      fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 4.46, w: 4.42, h: 2.08,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('问卷要收集的维度', {
    x: 0.84, y: 4.62, w: 2.6, h: 0.18,
    fontSize: 8.8, bold: true, color: C.ink, margin: 0
  });
  const profileDims = [
    ['投资目标', '保值、稳健增值还是追求收益'],
    ['投资期限', '短期要用钱，还是可长期不动'],
    ['流动性需求', '能否接受封闭期与赎回限制'],
    ['承受能力 / 意愿', '能亏多少是能力，愿亏多少是意愿'],
    ['投资经验', '是否理解波动与产品结构']
  ];
  profileDims.forEach((item, index) => {
    const y = 4.88 + index * 0.32;
    slide.addText('·', {
      x: 0.84, y: y, w: 0.14, h: 0.16,
      fontSize: 8.0, bold: true, color: C.teal, margin: 0
    });
    slide.addText(item[0], {
      x: 1.0, y: y, w: 1.0, h: 0.16,
      fontSize: 7.4, bold: true, color: C.navy2, margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 2.04, y: y, w: 2.8, h: 0.16,
      fontSize: 7.0, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：确定性评估规则。
  slide.addText('2  定级由规则完成', {
    x: 5.24, y: 2.02, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 5.24, y: 2.4, w: 3.7, h: 2.6,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 5.24, y: 2.4, w: 3.7, h: 0.4,
    fill: { color: C.navy2 }, line: { color: C.navy2 }
  });
  slide.addText('assess_risk_profile 的输入输出', {
    x: 5.46, y: 2.52, w: 3.3, h: 0.18,
    fontSize: 8.4, bold: true, color: C.white, margin: 0, fit: 'shrink'
  });
  slide.addText('输入\n  goal, horizon_months,\n  liquidity_need,\n  loss_capacity, loss_willingness,\n  experience\n\n输出\n  level: C1 | C2 | C3 | C4 | C5\n  valid_until: 2027-10-01\n  basis: 依据的问卷字段', {
    x: 5.46, y: 2.88, w: 3.3, h: 2.04,
    fontFace: 'Consolas', fontSize: 7.0, color: C.ink,
    margin: 0, valign: 'top', fit: 'shrink'
  });

  const profileRules = [
    ['历史行为不参与定级', '转账与消费记录最多用于辅助提示，不能自动提高等级', C.red, 'F9E7E5'],
    ['教学问卷 ≠ 正式测评', '简短问卷只作演示；正式适当性测评有自己的流程与留痕要求', C.amber, 'FBF1D8']
  ];
  profileRules.forEach((item, index) => {
    const y = 5.14 + index * 0.7;
    slide.addShape(S.roundRect, {
      x: 5.24, y, w: 3.7, h: 0.62,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 5.46, y: y + 0.08, w: 3.3, h: 0.18,
      fontSize: 8.4, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 5.46, y: y + 0.28, w: 3.3, h: 0.3,
      fontSize: 7.2, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 右栏：流程与等级表。
  slide.addText('3  测评流程', {
    x: 9.16, y: 2.02, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const profileFlow = [
    ['1', '先查有没有有效画像', C.green],
    ['2', '没有则收集五类信息', C.purple],
    ['3', '用规则算出 C1–C5', C.navy2],
    ['4', '写入有效期与依据', C.teal],
    ['5', '信息不足则只做客观介绍', C.amber]
  ];
  profileFlow.forEach((item, index) => {
    const y = 2.4 + index * 0.52;
    slide.addShape(S.roundRect, {
      x: 9.16, y, w: 3.57, h: 0.44,
      rectRadius: 0.03,
      fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
    });
    slide.addShape(S.ellipse, {
      x: 9.32, y: y + 0.09, w: 0.26, h: 0.26,
      fill: { color: item[2] }, line: { color: item[2] }
    });
    slide.addText(item[0], {
      x: 9.32, y: y + 0.16, w: 0.26, h: 0.11,
      fontSize: 6.6, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 9.68, y: y + 0.12, w: 2.9, h: 0.2,
      fontSize: 8.0, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 9.16, y: 5.08, w: 3.57, h: 1.46,
    rectRadius: 0.04,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('五个等级与适配关系', {
    x: 9.38, y: 5.22, w: 3.15, h: 0.18,
    fontSize: 8.8, bold: true, color: C.purple, margin: 0
  });
  const levels = [
    ['C1 保守', '只能 R1'],
    ['C2 稳健', 'R1–R2'],
    ['C3 平衡', 'R1–R3'],
    ['C4 成长', 'R1–R4'],
    ['C5 进取', 'R1–R5']
  ];
  levels.forEach((item, index) => {
    const y = 5.46 + index * 0.21;
    slide.addText(item[0], {
      x: 9.38, y, w: 1.1, h: 0.16,
      fontSize: 7.2, bold: true, color: C.navy2, margin: 0
    });
    slide.addText(item[1], {
      x: 10.5, y, w: 1.2, h: 0.16,
      fontSize: 7.2, color: C.muted, margin: 0
    });
  });
  slide.addText('产品等级不得高于用户等级：这条规则在检索阶段就生效。', {
    x: 9.38, y: 6.02, w: 3.15, h: 0.34,
    fontSize: 7.0, bold: true, color: C.purple, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.6, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('没有有效画像就不能推荐；历史行为只能辅助，不能自动提高风险等级', {
    x: 0.93, y: 6.69, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.red, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('21', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第二十二页：理财场景（下）产品筛选与申购分离
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('SCENARIO TOOLS · PRODUCTS', {
    x: 0.62, y: 0.42, w: 4.4, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('理财（下）：筛选是硬过滤，申购必须单独确认', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 1.24, w: 12.11, h: 0.32,
    rectRadius: 0.035,
    fill: { color: 'E5F2F0' }, line: { color: C.teal, width: 1 }
  });
  slide.addText('复杂度 4.5/5　　|　　[设计目标，待实现]　推荐与申购分离是本页的核心结论', {
    x: 0.93, y: 1.33, w: 11.5, h: 0.15,
    fontSize: 8.2, bold: true, color: C.teal, align: 'center', margin: 0
  });
  slide.addText('适当性过滤不合格的产品，模型连看到的机会都不该有——过滤要在检索阶段完成。', {
    x: 0.62, y: 1.63, w: 11.8, h: 0.24,
    fontSize: 10, color: C.muted, margin: 0
  });

  // 左栏：工具清单。
  slide.addText('1  需要哪些工具', {
    x: 0.62, y: 2.02, w: 2.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const productTools = [
    ['search_products', '按风险等级、期限、类型筛选候选', C.navy2, 'E9F1F7'],
    ['get_product_detail', '取说明书要点、费率、风险揭示', C.purple, 'EFE9F6'],
    ['compare_products', '同维度对比多个候选', C.teal, 'E5F2F0'],
    ['create_order', '生成申购申请单，需另行确认', C.amber, 'FBF1D8'],
    ['get_order_status', '确认申购是否受理与成立', C.green, 'E8F3EC']
  ];
  productTools.forEach((item, index) => {
    const y = 2.4 + index * 0.86;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 0.78,
      rectRadius: 0.035,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 0.84, y: y + 0.12, w: 2.6, h: 0.18,
      fontFace: 'Consolas', fontSize: 8.8, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 0.84, y: y + 0.36, w: 4.0, h: 0.34,
      fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：硬过滤示意。
  slide.addText('2  筛选先在服务端硬过滤', {
    x: 5.24, y: 2.02, w: 3.6, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 5.24, y: 2.4, w: 3.7, h: 1.0,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1.1 }
  });
  slide.addText('传入过滤条件，而不是事后判断', {
    x: 5.46, y: 2.54, w: 3.3, h: 0.18,
    fontSize: 8.6, bold: true, color: C.red, margin: 0, fit: 'shrink'
  });
  slide.addText('search_products(max_risk="R3", ...)：级别高于用户画像的产品根本不出现在候选里，模型无法推荐它。', {
    x: 5.46, y: 2.76, w: 3.3, h: 0.56,
    fontSize: 7.4, color: C.red, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 3.52, w: 3.7, h: 1.4,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('返回的候选（已按画像过滤）', {
    x: 5.46, y: 3.66, w: 3.3, h: 0.18,
    fontSize: 8.6, bold: true, color: C.ink, margin: 0
  });
  slide.addText('[\n  {"code": "R2-001", "level": "R2",\n   "term_days": 90, "fee": 0.0020},\n  {"code": "R3-014", "level": "R3",\n   "term_days": 365, "fee": 0.0045}\n]', {
    x: 5.46, y: 3.9, w: 3.3, h: 0.9,
    fontFace: 'Consolas', fontSize: 7.0, color: C.ink,
    margin: 0, valign: 'top', fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 5.04, w: 3.7, h: 1.5,
    rectRadius: 0.04,
    fill: { color: 'FBF1D8' }, line: { color: C.amber, width: 1 }
  });
  slide.addText('信息不足时的措辞边界', {
    x: 5.46, y: 5.18, w: 3.3, h: 0.18,
    fontSize: 8.6, bold: true, color: C.amber, margin: 0
  });
  slide.addText('可以做：说明产品类型、期限、费率结构、风险揭示要点。\n\n不可以做：宣称"这款更适合你"、"按你的情况建议买这只"。', {
    x: 5.46, y: 5.42, w: 3.3, h: 1.02,
    fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
  });

  // 右栏：推荐与申购分离。
  slide.addText('3  推荐与申购必须分离', {
    x: 9.16, y: 2.02, w: 3.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 9.16, y: 2.4, w: 3.57, h: 1.5,
    rectRadius: 0.04,
    fill: { color: 'E8F3EC' }, line: { color: C.green, width: 1 }
  });
  slide.addText('推荐阶段', {
    x: 9.38, y: 2.54, w: 2.4, h: 0.2,
    fontSize: 9.4, bold: true, color: C.green, margin: 0
  });
  slide.addText('· 只读工具：search / detail / compare\n· 输出候选与客观差异\n· 不产生任何资金变动\n· 明确标注"仅供参考"', {
    x: 9.38, y: 2.8, w: 3.15, h: 1.0,
    fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 9.16, y: 4.02, w: 3.57, h: 1.5,
    rectRadius: 0.04,
    fill: { color: 'FBF1D8' }, line: { color: C.amber, width: 1 }
  });
  slide.addText('申购阶段', {
    x: 9.38, y: 4.16, w: 2.4, h: 0.2,
    fontSize: 9.4, bold: true, color: C.amber, margin: 0
  });
  slide.addText('· create_order 只生成申请单\n· 金额、产品、费率必须二次展示\n· 用户独立确认后才提交\n· 状态查询确认是否成立', {
    x: 9.38, y: 4.42, w: 3.15, h: 1.0,
    fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 9.16, y: 5.64, w: 3.57, h: 0.9,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('不给模型的工具', {
    x: 9.38, y: 5.76, w: 2.4, h: 0.18,
    fontSize: 8.6, bold: true, color: C.red, margin: 0
  });
  slide.addText('直接申购、修改持仓、赎回执行；这些都必须在独立确认流程中完成。', {
    x: 9.38, y: 5.98, w: 3.15, h: 0.5,
    fontSize: 7.4, color: C.red, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.6, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('推荐是表达，申购是交易；把两者放进同一个工具或同一轮回复，就是安全漏洞', {
    x: 0.93, y: 6.69, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('22', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第二十三页：跨场景联动（上）长任务与 DAG
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('SCENARIO TOOLS · CROSS-SCENARIO', {
    x: 0.62, y: 0.42, w: 4.6, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('跨场景联动（上）：长任务不是一次对话能装下的', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 1.24, w: 12.11, h: 0.32,
    rectRadius: 0.035,
    fill: { color: 'E5F2F0' }, line: { color: C.teal, width: 1 }
  });
  slide.addText('复杂度 5/5　　|　　[设计目标，待实现]　本节分两页：本页讲任务模型，下页讲失败处理', {
    x: 0.93, y: 1.33, w: 11.5, h: 0.15,
    fontSize: 8.2, bold: true, color: C.teal, align: 'center', margin: 0
  });
  slide.addText('典型例子：先核实重复扣款，确认后停扣，再把结余自动转入理财——横跨账单、订阅、理财三个场景。', {
    x: 0.62, y: 1.63, w: 11.8, h: 0.24,
    fontSize: 10, color: C.muted, margin: 0
  });

  // 左栏：任务 DAG。
  slide.addText('1  任务是一张 DAG', {
    x: 0.62, y: 2.02, w: 2.6, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 0.62, y: 2.4, w: 4.42, h: 4.14,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  const dagNodes = [
    ['TRIGGER', '定时或事件唤醒', C.navy2, 2.58],
    ['get_bills', '核实重复扣款', C.purple, 3.32],
    ['condition', '命中重复扣款？', C.amber, 4.06],
    ['request_cancellation', '提交停扣申请', C.red, 4.8],
    ['notify_user', '告知进展与下一步', C.teal, 5.54]
  ];
  dagNodes.forEach((item, index) => {
    const isCondition = item[0] === 'condition';
    slide.addShape(isCondition ? S.rect : S.roundRect, {
      x: 0.84, y: item[3], w: 3.98, h: 0.56,
      rectRadius: 0.035,
      fill: { color: 'F6F8FA' }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 1.02, y: item[3] + 0.1, w: 1.9, h: 0.18,
      fontFace: 'Consolas', fontSize: 8.2, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 1.02, y: item[3] + 0.3, w: 3.6, h: 0.18,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
    if (index < dagNodes.length - 1) {
      slide.addShape(S.line, {
        x: 2.83, y: item[3] + 0.56, w: 0, h: 0.18,
        line: { color: '98A5AF', width: 1, endArrowType: 'triangle' }
      });
    }
  });
  slide.addText('条件不命中则跳过后续节点，任务直接进入已完成状态。', {
    x: 0.84, y: 6.16, w: 3.98, h: 0.3,
    fontSize: 7.4, italic: true, color: C.muted, margin: 0, fit: 'shrink'
  });

  // 中栏：任务定义字段。
  slide.addText('2  任务在数据库里长什么样', {
    x: 5.24, y: 2.02, w: 3.8, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 5.24, y: 2.4, w: 3.7, h: 2.3,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 5.24, y: 2.4, w: 3.7, h: 0.4,
    fill: { color: C.navy2 }, line: { color: C.navy2 }
  });
  slide.addText('agent_task 表', {
    x: 5.46, y: 2.52, w: 2.4, h: 0.18,
    fontFace: 'Consolas', fontSize: 8.8, bold: true, color: C.white, margin: 0
  });
  slide.addText('task_id        唯一标识，幂等键\nuser_id        归属，来自会话\nthread_id      可追溯到原始对话\ntrigger_type   schedule | event\ndag            节点与依赖定义\nnext_run_at    下次唤醒时间\nstatus         任务状态机\nauth_state     已授权到哪个节点\ncreated_at / updated_at', {
    x: 5.46, y: 2.88, w: 3.3, h: 1.74,
    fontFace: 'Consolas', fontSize: 7.0, color: C.ink,
    margin: 0, valign: 'top', fit: 'shrink'
  });

  const taskConds = [
    ['三个必须成立的条件', '任务落在业务库、逐节点授权、每次唤醒记审计', C.green, 'E8F3EC']
  ];
  taskConds.forEach((item) => {
    slide.addShape(S.roundRect, {
      x: 5.24, y: 4.86, w: 3.7, h: 0.71,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 5.46, y: 4.96, w: 3.3, h: 0.18,
      fontSize: 8.6, bold: true, color: item[2], margin: 0
    });
    slide.addText(item[1], {
      x: 5.46, y: 5.16, w: 3.3, h: 0.4,
      fontSize: 7.3, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 5.73, w: 3.7, h: 0.81,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('唤醒频率与并发上限', {
    x: 5.46, y: 5.85, w: 3.3, h: 0.18,
    fontSize: 8.4, bold: true, color: C.red, margin: 0
  });
  slide.addText('定时唤醒要限频、要加锁，避免同一任务被并发执行两次。', {
    x: 5.46, y: 6.05, w: 3.3, h: 0.42,
    fontSize: 7.2, color: C.red, margin: 0, fit: 'shrink'
  });

  // 右栏：任务状态机。
  slide.addText('3  任务状态机', {
    x: 9.16, y: 2.02, w: 2.6, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const taskStates = [
    ['PENDING', '已创建，等待首次唤醒', C.navy2, 'E9F1F7'],
    ['RUNNING', '正在执行某个节点', C.teal, 'E5F2F0'],
    ['WAITING_AUTH', '某节点需要用户确认', C.amber, 'FBF1D8'],
    ['SUCCEEDED', '全部节点成功完成', C.green, 'E8F3EC'],
    ['FAILED', '重试耗尽，需人工处理', C.red, 'F9E7E5']
  ];
  taskStates.forEach((item, index) => {
    const y = 2.4 + index * 0.82;
    slide.addShape(S.roundRect, {
      x: 9.16, y, w: 3.57, h: 0.72,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 9.38, y: y + 0.12, w: 3.15, h: 0.2,
      fontFace: 'Consolas', fontSize: 9.0, bold: true, color: item[2], margin: 0
    });
    slide.addText(item[1], {
      x: 9.38, y: y + 0.36, w: 3.15, h: 0.28,
      fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.6, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('长任务不能依赖 LangGraph 的对话 Checkpoint：必须有自己的 task_id 与持久化状态', {
    x: 0.93, y: 6.69, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.red, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('23', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第二十四页：跨场景联动（下）重试与补偿
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('SCENARIO TOOLS · RECOVERY', {
    x: 0.62, y: 0.42, w: 4.4, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('跨场景联动（下）：失败、重试与部分成功', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 1.24, w: 12.11, h: 0.32,
    rectRadius: 0.035,
    fill: { color: 'E5F2F0' }, line: { color: C.teal, width: 1 }
  });
  slide.addText('复杂度 5/5　　|　　[设计目标，待实现]　长任务的失败是常态，不是异常', {
    x: 0.93, y: 1.33, w: 11.5, h: 0.15,
    fontSize: 8.2, bold: true, color: C.teal, align: 'center', margin: 0
  });
  slide.addText('DAG 走到一半失败时，最危险的不是失败本身，而是"已经做了一部分却当成全部失败"。', {
    x: 0.62, y: 1.63, w: 11.8, h: 0.24,
    fontSize: 10, color: C.muted, margin: 0
  });

  // 左栏：什么可以重试。
  slide.addText('1  按可重试性给操作分类', {
    x: 0.62, y: 2.02, w: 3.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const retryClasses = [
    {
      title: '可以重试', color: C.green, fill: 'E8F3EC',
      items: ['查询类操作（读余额、查状态）', '通知类操作（可重复发送）', '纯计算与聚合']
    },
    {
      title: '必须靠幂等键重试', color: C.amber, fill: 'FBF1D8',
      items: ['转账、代扣、申购等写操作', '同一 request_id 重复提交只生效一次', '重试前先查原请求结果']
    },
    {
      title: '不能重试', color: C.red, fill: 'F9E7E5',
      items: ['已确认完成的不可逆动作', '挂失、销户等终态操作', '重试会造成二次副作用的步骤']
    }
  ];
  retryClasses.forEach((item, index) => {
    const y = 2.4 + index * 1.4;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 1.28,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 0.84, y: y + 0.12, w: 4.0, h: 0.2,
      fontSize: 9.4, bold: true, color: item.color, margin: 0
    });
    slide.addText(item.items.map((line) => '· ' + line).join('\n'), {
      x: 0.84, y: y + 0.36, w: 4.0, h: 0.84,
      fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：重试策略与补偿。
  slide.addText('2  重试策略与补偿', {
    x: 5.24, y: 2.02, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 5.24, y: 2.4, w: 3.7, h: 1.5,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('重试要有上限和退避', {
    x: 5.46, y: 2.54, w: 3.3, h: 0.18,
    fontSize: 8.8, bold: true, color: C.ink, margin: 0
  });
  slide.addText('· 指数退避，避免打爆下游\n· 最大次数用尽 → FAILED\n· 进入死信队列等待人工处理\n· 每次重试都留审计记录', {
    x: 5.46, y: 2.78, w: 3.3, h: 1.0,
    fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 4.02, w: 3.7, h: 1.5,
    rectRadius: 0.04,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('补偿是反向操作，不是重试', {
    x: 5.46, y: 4.16, w: 3.3, h: 0.18,
    fontSize: 8.8, bold: true, color: C.purple, margin: 0
  });
  slide.addText('· 停扣失败但申购已完成 → 需要撤单\n· 补偿本身也可能失败，同样要留痕\n· 补偿要幂等，并且可审计\n· 无法自动补偿时转人工', {
    x: 5.46, y: 4.4, w: 3.3, h: 1.0,
    fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 5.64, w: 3.7, h: 0.9,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('为什么需要人工接管', {
    x: 5.46, y: 5.76, w: 3.3, h: 0.18,
    fontSize: 8.6, bold: true, color: C.red, margin: 0
  });
  slide.addText('部分成功、跨系统不一致、补偿失败的场景，必须有人能接手并留下处理记录。', {
    x: 5.46, y: 5.98, w: 3.3, h: 0.5,
    fontSize: 7.3, color: C.red, margin: 0, fit: 'shrink'
  });

  // 右栏：部分成功的处理。
  slide.addText('3  部分成功怎么记', {
    x: 9.16, y: 2.02, w: 2.8, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const partialFlow = [
    ['1', '节点逐个记录结果', '每个节点独立写入状态，不共用一把大事务', C.navy2],
    ['2', '失败即停在当前节点', '后续节点不再执行，避免雪崩', C.amber],
    ['3', '按已成功部分决定去向', '能补偿则补偿，不能则转人工', C.purple],
    ['4', '对用户如实表述', '已完成什么、未完成什么，不含糊', C.teal]
  ];
  partialFlow.forEach((item, index) => {
    const y = 2.4 + index * 1.04;
    slide.addShape(S.roundRect, {
      x: 9.16, y, w: 3.57, h: 0.92,
      rectRadius: 0.04,
      fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
    });
    slide.addShape(S.ellipse, {
      x: 9.36, y: y + 0.14, w: 0.3, h: 0.3,
      fill: { color: item[3] }, line: { color: item[3] }
    });
    slide.addText(item[0], {
      x: 9.36, y: y + 0.22, w: 0.3, h: 0.12,
      fontSize: 6.8, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 9.78, y: y + 0.13, w: 2.8, h: 0.18,
      fontSize: 8.6, bold: true, color: C.ink, margin: 0, fit: 'shrink'
    });
    slide.addText(item[2], {
      x: 9.78, y: y + 0.35, w: 2.8, h: 0.44,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
    if (index < partialFlow.length - 1) {
      slide.addShape(S.line, {
        x: 9.51, y: y + 0.3, w: 0, h: 0.74,
        line: { color: '98A5AF', width: 1, endArrowType: 'triangle' }
      });
    }
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.6, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('重试要有上限，补偿要有幂等，失败要能转人工；三者缺一，长任务就不能上生产', {
    x: 0.93, y: 6.69, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('24', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第二十五页：模拟数据准备流水线
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('DATA · PIPELINE', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('模拟数据准备：先生成事实，再谈智能', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('开发期跑一次，产出可推导结论的底层业务事实，供所有场景与演示重复使用。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：六步流水线。
  slide.addText('1  六步流水线', {
    x: 0.62, y: 1.72, w: 2.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const dataPipeline = [
    ['01', '设计典型用户画像', '新开户、稳健白领、家庭用户、自由职业者'],
    ['02', '建基础实体', '账户、卡片、联系人、产品、代扣协议'],
    ['03', '生成资金流水', '工资、固定支出、日常消费、周期扣款、申购赎回'],
    ['04', '固定种子与参考日期', '使用固定随机种子与统一参考日期，保证可重复'],
    ['05', '注入剧情', '重复扣款、异常大额等需要被发现的场景'],
    ['06', '一致性校验后交付', '校验通过才写入业务库，供 API 使用']
  ];
  dataPipeline.forEach((item, index) => {
    const y = 2.12 + index * 0.56;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 3.9, h: 0.48,
      rectRadius: 0.03,
      fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
    });
    slide.addShape(S.ellipse, {
      x: 0.78, y: y + 0.12, w: 0.24, h: 0.24,
      fill: { color: C.navy2 }, line: { color: C.navy2 }
    });
    slide.addText(item[0], {
      x: 0.78, y: y + 0.18, w: 0.24, h: 0.1,
      fontSize: 6.2, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 1.1, y: y + 0.06, w: 3.3, h: 0.16,
      fontSize: 7.8, bold: true, color: C.ink, margin: 0, fit: 'shrink'
    });
    slide.addText(item[2], {
      x: 1.1, y: y + 0.24, w: 3.3, h: 0.18,
      fontSize: 6.9, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：演示规模与原则。
  slide.addText('2  演示规模', {
    x: 4.82, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 4.82, y: 2.12, w: 3.7, h: 2.3,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addText('典型用户画像', {
    x: 5.04, y: 2.28, w: 3.3, h: 0.18,
    fontSize: 8.8, bold: true, color: C.navy2, margin: 0
  });
  slide.addText('6 ～ 8 个，覆盖不同收支结构与风险偏好', {
    x: 5.04, y: 2.5, w: 3.3, h: 0.2,
    fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
  });
  slide.addText('时间跨度', {
    x: 5.04, y: 2.84, w: 3.3, h: 0.18,
    fontSize: 8.8, bold: true, color: C.navy2, margin: 0
  });
  slide.addText('约 12 个月，足以体现月度周期与年度特征', {
    x: 5.04, y: 3.06, w: 3.3, h: 0.2,
    fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
  });
  slide.addText('产品与协议', {
    x: 5.04, y: 3.4, w: 3.3, h: 0.18,
    fontSize: 8.8, bold: true, color: C.navy2, margin: 0
  });
  slide.addText('12 ～ 20 个产品，覆盖 R1–R5；若干代扣协议', {
    x: 5.04, y: 3.62, w: 3.3, h: 0.2,
    fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
  });
  slide.addShape(S.line, {
    x: 5.04, y: 3.98, w: 3.26, h: 0,
    line: { color: C.line, width: 1 }
  });
  slide.addText('规模只需覆盖演示剧情，不必逼近真实体量。', {
    x: 5.04, y: 4.08, w: 3.3, h: 0.28,
    fontSize: 7.2, italic: true, color: C.muted, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 4.82, y: 4.6, w: 3.7, h: 1.94,
    rectRadius: 0.04,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('核心原则', {
    x: 5.04, y: 4.76, w: 2.4, h: 0.18,
    fontSize: 8.8, bold: true, color: C.purple, margin: 0
  });
  slide.addText('先生成能推导结论的底层业务事实，不让模型临时编造余额、账单或理财习惯。', {
    x: 5.04, y: 5.0, w: 3.3, h: 0.6,
    fontSize: 7.8, color: C.ink, margin: 0, fit: 'shrink'
  });
  slide.addText('数据是"事实层"，模型的表述必须能回溯到这些记录。', {
    x: 5.04, y: 5.68, w: 3.3, h: 0.5,
    fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
  });

  // 右栏：为什么是独立模块。
  slide.addText('3  为什么是独立模块', {
    x: 8.82, y: 1.72, w: 2.8, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const dataWhy = [
    {
      title: '只在开发期运行一次', color: C.green, fill: 'E8F3EC',
      desc: '产出的数据落进业务库；运行时不重新生成，避免演示时结果每次都变。'
    },
    {
      title: '运行时不信任任何历史值', color: C.amber, fill: 'FBF1D8',
      desc: '业务服务每次仍要重新读取余额、状态、授权与幂等；生成的数据不等于当前真相。'
    },
    {
      title: '可重复是硬要求', color: C.navy2, fill: 'E9F1F7',
      desc: '固定种子与统一参考日期，才能让"同一句话每次得到同一结果"用于测试与演示。'
    }
  ];
  dataWhy.forEach((item, index) => {
    const y = 2.12 + index * 1.34;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.91, h: 1.22,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 9.04, y: y + 0.12, w: 3.5, h: 0.2,
      fontSize: 9.0, bold: true, color: item.color, margin: 0, fit: 'shrink'
    });
    slide.addText(item.desc, {
      x: 9.04, y: y + 0.38, w: 3.5, h: 0.74,
      fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 8.82, y: 6.14, w: 3.91, h: 0.4,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('模拟数据生成  与  运行时校验  是两件事', {
    x: 9.04, y: 6.25, w: 3.5, h: 0.18,
    fontSize: 8.0, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('25', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第二十六页：一致性与真值隔离
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('DATA · INTEGRITY', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('一致性校验与真值隔离：数据错了，后面全错', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('生成的数据必须先通过确定性校验，才能交给业务 API；异常标签只能留在测试侧。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：校验项。
  slide.addText('1  必须校验什么', {
    x: 0.62, y: 1.72, w: 2.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const checks = [
    ['余额 ↔ 账本', '账户余额必须等于账本流水累计，逐笔可对'],
    ['订单 ↔ 持仓', '申购订单必须对应到持仓份额，不能凭空多出'],
    ['订阅状态', '代扣协议状态与最近扣款记录必须自洽'],
    ['外键完整', '账户、卡片、联系人、产品之间不能有悬挂引用'],
    ['时间顺序', '不能出现先扣款后签约、或未来日期的流水'],
    ['金额精度', '前端展示与库内存储必须使用同一精度口径']
  ];
  checks.forEach((item, index) => {
    const y = 2.12 + index * 0.56;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 0.48,
      rectRadius: 0.03,
      fill: { color: index === 5 ? 'FBF1D8' : 'FFFFFF' },
      line: { color: index === 5 ? C.amber : 'C8D4DE', width: 1 }
    });
    slide.addText(item[0], {
      x: 0.84, y: y + 0.06, w: 1.5, h: 0.16,
      fontSize: 7.8, bold: true, color: index === 5 ? C.amber : C.navy2, margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 0.84, y: y + 0.25, w: 4.0, h: 0.18,
      fontSize: 6.9, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：真值隔离与金额精度。
  slide.addText('2  真值标签的处置', {
    x: 5.24, y: 1.72, w: 2.8, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 5.24, y: 2.12, w: 3.7, h: 2.3,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1.1 }
  });
  slide.addText('异常真值只供测试', {
    x: 5.46, y: 2.28, w: 3.3, h: 0.2,
    fontSize: 9.2, bold: true, color: C.red, margin: 0
  });
  slide.addText('生成数据时会主动注入重复扣款、异常大额等剧情，同时记录"哪几笔是异常"的答案。', {
    x: 5.46, y: 2.54, w: 3.3, h: 0.56,
    fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
  });
  slide.addShape(S.line, {
    x: 5.46, y: 3.16, w: 3.26, h: 0,
    line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('这份答案不能进入业务库、不能出现在工具返回、不能写进 RAG；它只用于自动比对检测结果是否准确。', {
    x: 5.46, y: 3.28, w: 3.3, h: 0.72,
    fontSize: 7.6, bold: true, color: C.red, margin: 0, fit: 'shrink'
  });
  slide.addText('一旦泄露给 Agent，异常检测就变成了抄答案。', {
    x: 5.46, y: 4.02, w: 3.3, h: 0.28,
    fontSize: 7.4, italic: true, color: C.red, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 4.6, w: 3.7, h: 1.94,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('金额精度：用 Decimal 或整数分', {
    x: 5.46, y: 4.76, w: 3.3, h: 0.2,
    fontSize: 8.8, bold: true, color: C.ink, margin: 0, fit: 'shrink'
  });
  slide.addText('教学示例用 float 只为缩短代码，真实资金计算必须避免二进制浮点误差。', {
    x: 5.46, y: 5.02, w: 3.3, h: 0.56,
    fontSize: 7.5, color: C.muted, margin: 0, fit: 'shrink'
  });
  slide.addText('0.1 + 0.2 != 0.3 这类误差在对账时会被放大成真实差错。', {
    x: 5.46, y: 5.66, w: 3.3, h: 0.5,
    fontSize: 7.5, bold: true, color: C.amber, margin: 0, fit: 'shrink'
  });
  slide.addText('校验通过是交付前提，不是可选项。', {
    x: 5.46, y: 6.16, w: 3.3, h: 0.28,
    fontSize: 7.4, italic: true, color: C.muted, margin: 0, fit: 'shrink'
  });

  // 右栏：数据流向。
  slide.addText('3  数据流向与前置条件', {
    x: 8.82, y: 1.72, w: 3.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const dataFlowSteps = [
    ['1', '设计画像与剧情', '确定要演示哪些结论', C.navy2],
    ['2', '生成实体与流水', '固定种子，可重复', C.purple],
    ['3', '跑一致性校验', '不通过就不交付', C.amber],
    ['4', '写入业务库', '供 API 与场景工具读取', C.teal],
    ['5', '真值单独留测试侧', '永不进入业务库', C.red]
  ];
  dataFlowSteps.forEach((item, index) => {
    const y = 2.12 + index * 0.76;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.91, h: 0.66,
      rectRadius: 0.04,
      fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
    });
    slide.addShape(S.ellipse, {
      x: 9.02, y: y + 0.16, w: 0.3, h: 0.3,
      fill: { color: item[3] }, line: { color: item[3] }
    });
    slide.addText(item[0], {
      x: 9.02, y: y + 0.24, w: 0.3, h: 0.12,
      fontSize: 6.8, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 9.44, y: y + 0.1, w: 3.1, h: 0.18,
      fontSize: 8.4, bold: true, color: C.ink, margin: 0, fit: 'shrink'
    });
    slide.addText(item[2], {
      x: 9.44, y: y + 0.32, w: 3.1, h: 0.28,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
    if (index < dataFlowSteps.length - 1) {
      slide.addShape(S.line, {
        x: 9.17, y: y + 0.3, w: 0, h: 0.46,
        line: { color: '98A5AF', width: 1, endArrowType: 'triangle' }
      });
    }
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.6, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('三条铁律：不让模型编造事实、不把异常真值暴露给 Agent、不跳过一致性校验', {
    x: 0.93, y: 6.69, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.red, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('26', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第二十七页：持久化，内存版与生产存储
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('PERSISTENCE', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('持久化：InMemorySaver 只适合跑通流程', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('教学版把 Checkpoint 放在内存里；进程一退出，暂停中的确认和认证就全部消失。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：内存版的限制。
  slide.addText('1  内存版能做什么、不能做什么', {
    x: 0.62, y: 1.72, w: 4.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const memLimits = [
    ['能', '在同一次进程运行内暂停与恢复，演示黄色确认与红色强认证', C.green, 'E8F3EC'],
    ['不能', '进程重启后恢复；没有持久化介质，状态随进程消失', C.red, 'F9E7E5'],
    ['注意', '必须复用编译好的图与同一个 saver 实例，重新 build 会得到空 saver', C.amber, 'FBF1D8'],
    ['注意', '多进程或多实例部署时，内存 Checkpoint 互相不可见', C.amber, 'FBF1D8']
  ];
  memLimits.forEach((item, index) => {
    const y = 2.12 + index * 1.06;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 0.96,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 0.84, y: y + 0.12, w: 0.7, h: 0.18,
      fontSize: 8.8, bold: true, color: item[2], margin: 0
    });
    slide.addText(item[1], {
      x: 0.84, y: y + 0.36, w: 4.0, h: 0.52,
      fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：四类存储各管什么。
  slide.addText('2  四类存储各管什么', {
    x: 5.24, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const stores = [
    ['业务数据库', '账户、卡片、交易、协议、订单与持仓', C.navy2, 'E9F1F7'],
    ['核心账本', '资金流水与余额的唯一真相来源', C.green, 'E8F3EC'],
    ['Checkpoint 库', '工作流快照与执行位置，可换 PostgreSQL', C.purple, 'EFE9F6'],
    ['政策知识库', '政策、FAQ、产品说明书，供 RAG 检索', C.teal, 'E5F2F0']
  ];
  stores.forEach((item, index) => {
    const y = 2.12 + index * 0.96;
    slide.addShape(S.roundRect, {
      x: 5.24, y, w: 3.7, h: 0.86,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 5.46, y: y + 0.1, w: 3.3, h: 0.2,
      fontSize: 9.0, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 5.46, y: y + 0.34, w: 3.3, h: 0.44,
      fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 5.96, w: 3.7, h: 0.58,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('Checkpoint 不是核心账本：恢复流程时仍要向业务系统重新确认交易状态。', {
    x: 5.46, y: 6.08, w: 3.3, h: 0.38,
    fontSize: 7.4, bold: true, color: C.red, margin: 0, fit: 'shrink'
  });

  // 右栏：部署形态差异。
  slide.addText('3  部署形态决定结果', {
    x: 8.82, y: 1.72, w: 3.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const deployments = [
    {
      title: '单进程演示', color: C.navy2, fill: 'E9F1F7',
      lines: ['uvicorn 单实例 + InMemorySaver', '暂停中的流程必须在本进程内恢复', '重启即丢失，需要重新发起']
    },
    {
      title: '生产部署', color: C.green, fill: 'E8F3EC',
      lines: ['PostgreSQL Checkpointer 持久化', '任意实例都能按 thread_id 恢复', '重启、扩容、滚动发布都不丢流程']
    },
    {
      title: '必须坚持的原则', color: C.amber, fill: 'FBF1D8',
      lines: ['授权与余额永远查业务系统', 'Checkpoint 只负责"走到哪了"', '幂等键防止恢复后重复执行']
    }
  ];
  deployments.forEach((item, index) => {
    const y = 2.12 + index * 1.5;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.91, h: 1.38,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 9.04, y: y + 0.12, w: 3.5, h: 0.2,
      fontSize: 9.2, bold: true, color: item.color, margin: 0
    });
    slide.addText(item.lines.map((line) => '· ' + line).join('\n'), {
      x: 9.04, y: y + 0.38, w: 3.5, h: 0.9,
      fontSize: 7.5, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.6, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('把 Checkpoint 存储换掉，图与节点代码不用改一行：这就是分层设计的好处', {
    x: 0.93, y: 6.69, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('27', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第二十八页：幂等与重复扣款
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('IDEMPOTENCY', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('幂等：超时不等于失败，重试不能扣两次', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('分布式系统里最贵的 bug：用户看到超时点了两次，钱扣了两笔。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：失败剧本。
  slide.addText('1  一次真实会发生的超时', {
    x: 0.62, y: 1.72, w: 3.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const timeoutStory = [
    ['1', '客户端提交转账请求', '携带 client_request_id', C.navy2],
    ['2', '服务端已完成扣款', '状态写入 COMPLETED', C.green],
    ['3', '响应在返回途中超时', '客户端只看到 timeout', C.red],
    ['4', '用户重试或重复点击', '同一个 request_id 再次到达', C.amber],
    ['5', '若没有幂等约束', '就会产生第二笔扣款', C.red]
  ];
  timeoutStory.forEach((item, index) => {
    const y = 2.12 + index * 0.76;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 0.66,
      rectRadius: 0.04,
      fill: { color: 'FFFFFF' }, line: { color: index >= 3 ? C.red : 'C8D4DE', width: 1 }
    });
    slide.addShape(S.ellipse, {
      x: 0.82, y: y + 0.16, w: 0.3, h: 0.3,
      fill: { color: item[3] }, line: { color: item[3] }
    });
    slide.addText(item[0], {
      x: 0.82, y: y + 0.24, w: 0.3, h: 0.12,
      fontSize: 6.8, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 1.24, y: y + 0.1, w: 3.6, h: 0.18,
      fontSize: 8.6, bold: true, color: C.ink, margin: 0, fit: 'shrink'
    });
    slide.addText(item[3], {
      x: 1.24, y: y + 0.32, w: 3.6, h: 0.18,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
    if (index < timeoutStory.length - 1) {
      slide.addShape(S.line, {
        x: 0.97, y: y + 0.3, w: 0, h: 0.46,
        line: { color: '98A5AF', width: 1, endArrowType: 'triangle' }
      });
    }
  });

  // 中栏：两道防线。
  slide.addText('2  两道防线', {
    x: 5.24, y: 1.72, w: 2.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 5.24, y: 2.12, w: 3.7, h: 2.0,
    rectRadius: 0.04,
    fill: { color: 'E8F3EC' }, line: { color: C.green, width: 1.1 }
  });
  slide.addText('防线一：唯一约束', {
    x: 5.46, y: 2.28, w: 3.3, h: 0.2,
    fontSize: 9.2, bold: true, color: C.green, margin: 0
  });
  slide.addText('数据库对 request_id（或幂等键）建唯一索引。第二次插入直接冲突，业务层据此返回原结果，而不是再执行一次。', {
    x: 5.46, y: 2.54, w: 3.3, h: 0.8,
    fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
  });
  slide.addText('UNIQUE(request_id)', {
    x: 5.46, y: 3.4, w: 3.3, h: 0.2,
    fontFace: 'Consolas', fontSize: 8.0, bold: true, color: C.green, margin: 0
  });
  slide.addText('约束在数据库层，代码写错也挡得住。', {
    x: 5.46, y: 3.66, w: 3.3, h: 0.3,
    fontSize: 7.4, italic: true, color: C.muted, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 4.28, w: 3.7, h: 1.5,
    rectRadius: 0.04,
    fill: { color: 'E9F1F7' }, line: { color: C.navy2, width: 1 }
  });
  slide.addText('防线二：先查后做', {
    x: 5.46, y: 4.42, w: 3.3, h: 0.2,
    fontSize: 9.2, bold: true, color: C.navy2, margin: 0
  });
  slide.addText('收到请求先查这个 request_id 是否已有结果：有则直接返回原结果；没有才进入执行。', {
    x: 5.46, y: 4.68, w: 3.3, h: 0.94,
    fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 5.94, w: 3.7, h: 0.6,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('两道防线要同时有：约束兜底，查询优化体验。', {
    x: 5.46, y: 6.06, w: 3.3, h: 0.4,
    fontSize: 7.6, bold: true, color: C.red, margin: 0, fit: 'shrink'
  });

  // 右栏：请求标识的三种角色。
  slide.addText('3  请求标识的三个角色', {
    x: 8.82, y: 1.72, w: 3.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const idRoles = [
    ['client_request_id', '客户端生成，用于识别"这是同一次提交"', C.purple, 'EFE9F6'],
    ['request_id', '服务端生成，进入操作哈希，参与审计', C.navy2, 'E9F1F7'],
    ['thread_id', '会话恢复键，与资金幂等无关，不能混用', C.amber, 'FBF1D8']
  ];
  idRoles.forEach((item, index) => {
    const y = 2.12 + index * 1.2;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.91, h: 1.08,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 9.04, y: y + 0.14, w: 3.5, h: 0.2,
      fontFace: 'Consolas', fontSize: 9.0, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 9.04, y: y + 0.4, w: 3.5, h: 0.56,
      fontSize: 7.5, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 8.82, y: 5.72, w: 3.91, h: 0.82,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('断线之后该做什么', {
    x: 9.04, y: 5.84, w: 3.5, h: 0.18,
    fontSize: 8.6, bold: true, color: C.ink, margin: 0
  });
  slide.addText('查询原任务状态，而不是重新提交一笔新转账；这也是 get_transfer_status 存在的意义。', {
    x: 9.04, y: 6.06, w: 3.5, h: 0.44,
    fontSize: 7.4, color: C.muted, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.14, w: 4.42, h: 0.4,
    rectRadius: 0.035,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('超时不是失败证据：必须靠幂等键判断真实结果', {
    x: 0.84, y: 6.25, w: 4.0, h: 0.18,
    fontSize: 8.0, bold: true, color: C.red, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('28', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第二十九页：审计与证据链
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('AUDIT', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('审计与证据链：每次判断都要能复盘', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('出问题时，需要回答的不是"模型说了什么"，而是"程序依据什么做了决定"。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：审计字段。
  slide.addText('1  一条审计记录包含什么', {
    x: 0.62, y: 1.72, w: 3.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 0.62, y: 2.12, w: 4.42, h: 2.36,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 0.62, y: 2.12, w: 4.42, h: 0.4,
    fill: { color: C.navy2 }, line: { color: C.navy2 }
  });
  slide.addText('audit_event', {
    x: 0.84, y: 2.24, w: 2.4, h: 0.18,
    fontFace: 'Consolas', fontSize: 8.8, bold: true, color: C.white, margin: 0
  });
  slide.addText('ts            发生时间\ntrace_id      全链路追踪\ntrace 关联\nuser_id       操作人\nthread_id     会话\nrequest_id    请求\nactor         user | agent | system\nevent         事件类型\ntool          工具名（若有）\nparams        脱敏后的参数\ndecision      判定结果\nresult_ref    业务结果引用', {
    x: 0.84, y: 2.6, w: 4.0, h: 1.8,
    fontFace: 'Consolas', fontSize: 6.9, color: C.ink,
    margin: 0, valign: 'top', fit: 'shrink'
  });

  const auditEvents = [
    ['必须记录的事件', '工具调用、确认、执行、失败、拒绝、政策拒绝、认证结果', C.red, 'F9E7E5'],
    ['必须能回答', '谁在什么时候、依据哪条规则、对哪笔操作做了什么决定', C.navy2, 'E9F1F7']
  ];
  auditEvents.forEach((item, index) => {
    const y = 4.62 + index * 0.94;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 0.84,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 0.84, y: y + 0.1, w: 4.0, h: 0.18,
      fontSize: 8.6, bold: true, color: item[2], margin: 0
    });
    slide.addText(item[1], {
      x: 0.84, y: y + 0.32, w: 4.0, h: 0.44,
      fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：证据链示例。
  slide.addText('2  一笔转账的证据链', {
    x: 5.24, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const evidenceChain = [
    ['1', '理解候选', 'intent=TRANSFER, amount=300', C.purple],
    ['2', '服务端解析', 'contact_id=contact-001', C.navy2],
    ['3', '计划与校验', 'PREPARE_TRANSFER, plan_valid', C.navy2],
    ['4', '风险定级', 'RED + operation_hash', C.amber],
    ['5', '强认证结果', 'authorized=true（认证服务）', C.red],
    ['6', '执行与余额', 'COMPLETED, remaining_balance', C.green],
    ['7', '对外回复', 'response 文本与 result 一致', C.teal]
  ];
  evidenceChain.forEach((item, index) => {
    const y = 2.12 + index * 0.56;
    slide.addShape(S.roundRect, {
      x: 5.24, y, w: 3.7, h: 0.48,
      rectRadius: 0.03,
      fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
    });
    slide.addShape(S.ellipse, {
      x: 5.4, y: y + 0.12, w: 0.24, h: 0.24,
      fill: { color: item[3] }, line: { color: item[3] }
    });
    slide.addText(item[0], {
      x: 5.4, y: y + 0.18, w: 0.24, h: 0.1,
      fontSize: 6.2, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 5.72, y: y + 0.06, w: 1.0, h: 0.16,
      fontSize: 7.4, bold: true, color: C.ink, margin: 0, fit: 'shrink'
    });
    slide.addText(item[3], {
      x: 6.74, y: y + 0.07, w: 2.06, h: 0.34,
      fontFace: 'Consolas', fontSize: 6.6, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 6.02, w: 3.7, h: 0.52,
    rectRadius: 0.035,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('七步串起来，才能解释"钱为什么动了"。', {
    x: 5.46, y: 6.14, w: 3.3, h: 0.3,
    fontSize: 7.6, bold: true, color: C.purple, margin: 0, fit: 'shrink'
  });

  // 右栏：保留与脱敏。
  slide.addText('3  保留与脱敏', {
    x: 8.82, y: 1.72, w: 2.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const auditRules = [
    {
      title: '永不落盘的字段', color: C.red, fill: 'F9E7E5',
      desc: '密码、OTP、支付密码、生物特征、令牌、私钥。它们不进入 Prompt、消息、ToolMessage、Checkpoint、日志与向量库。'
    },
    {
      title: '必须脱敏的字段', color: C.amber, fill: 'FBF1D8',
      desc: '卡号只留后四位、手机号中间打码、身份证只留首尾；参数入审计前先脱敏。'
    },
    {
      title: '保留期与访问控制', color: C.navy2, fill: 'E9F1F7',
      desc: '审计日志需要保留期与访问权限；谁能查、能查多久，都要有规则，而不是人人可读。'
    },
    {
      title: '与业务结果关联', color: C.green, fill: 'E8F3EC',
      desc: '审计条目引用业务结果 ID，但不复制余额等易变事实，避免出现两份互相矛盾的真相。'
    }
  ];
  auditRules.forEach((item, index) => {
    const y = 2.12 + index * 1.06;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.91, h: 0.96,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 9.04, y: y + 0.1, w: 3.5, h: 0.2,
      fontSize: 8.8, bold: true, color: item.color, margin: 0, fit: 'shrink'
    });
    slide.addText(item.desc, {
      x: 9.04, y: y + 0.32, w: 3.5, h: 0.6,
      fontSize: 7.3, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.6, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('敏感信息不进模型、不进日志、不进向量库；审计记录的是决定与依据，不是密码', {
    x: 0.93, y: 6.69, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.red, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('29', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第三十页：安全总览（上）Prompt 注入与权限
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('SECURITY · OVERVIEW 1/2', {
    x: 0.62, y: 0.42, w: 4.0, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('提示注入改变不了权限，只可能改变措辞', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('安全边界不靠提示词声明，而靠代码结构、工具清单和服务端校验共同保证。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：三层信任。
  slide.addText('1  信任分层', {
    x: 0.62, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const trustLayers = [
    {
      title: '不可信输入', color: C.red, fill: 'F9E7E5',
      items: ['用户自然语言 message', '上传的截图与文件内容', '前端可编辑的一切字段']
    },
    {
      title: '候选层（解析产物）', color: C.purple, fill: 'EFE9F6',
      items: ['intent、recipient_name、amount', 'missing_fields', '仅供后续校验，不得直接执行']
    },
    {
      title: '可信层（服务端生成）', color: C.green, fill: 'E8F3EC',
      items: ['user_id、account_id（Session）', 'contact_id、risk_level、operation_hash', 'authorized、result']
    }
  ];
  trustLayers.forEach((item, index) => {
    const y = 2.12 + index * 1.38;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 1.26,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 0.84, y: y + 0.12, w: 4.0, h: 0.2,
      fontSize: 9.2, bold: true, color: item.color, margin: 0
    });
    slide.addText(item.items.map((line) => '· ' + line).join('\n'), {
      x: 0.84, y: y + 0.36, w: 4.0, h: 0.82,
      fontSize: 7.5, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：注入能做什么、不能做什么。
  slide.addText('2  注入的影响边界', {
    x: 5.24, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 5.24, y: 2.12, w: 3.7, h: 1.6,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1.1 }
  });
  slide.addText('注入可能导致', {
    x: 5.46, y: 2.26, w: 3.3, h: 0.2,
    fontSize: 9.0, bold: true, color: C.red, margin: 0
  });
  slide.addText('· 候选字段被误导（填错收款人）\n· 回复措辞被带偏\n· 模型提出不该提的工具调用请求', {
    x: 5.46, y: 2.5, w: 3.3, h: 0.7,
    fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
  });
  slide.addText('这些都在"候选层"，还会被后续节点复核。', {
    x: 5.46, y: 3.24, w: 3.3, h: 0.4,
    fontSize: 7.4, italic: true, color: C.red, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 3.88, w: 3.7, h: 1.6,
    rectRadius: 0.04,
    fill: { color: 'E8F3EC' }, line: { color: C.green, width: 1.1 }
  });
  slide.addText('注入改变不了的', {
    x: 5.46, y: 4.02, w: 3.3, h: 0.2,
    fontSize: 9.0, bold: true, color: C.green, margin: 0
  });
  slide.addText('· 工具白名单与调用权限\n· 风险等级与限额阈值\n· 身份来源（Session 而非消息）\n· 幂等键与审计要求', {
    x: 5.46, y: 4.26, w: 3.3, h: 0.98,
    fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 5.64, w: 3.7, h: 0.9,
    rectRadius: 0.04,
    fill: { color: 'FBF1D8' }, line: { color: C.amber, width: 1 }
  });
  slide.addText('"我是管理员"这句话没有权限含义', {
    x: 5.46, y: 5.76, w: 3.3, h: 0.2,
    fontSize: 8.4, bold: true, color: C.amber, margin: 0, fit: 'shrink'
  });
  slide.addText('身份只来自服务端认证上下文；消息里的自称不进入任何判定。', {
    x: 5.46, y: 5.98, w: 3.3, h: 0.5,
    fontSize: 7.3, color: C.ink, margin: 0, fit: 'shrink'
  });

  // 右栏：四层校验。
  slide.addText('3  四层校验，层层收窄', {
    x: 8.82, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const securityLayers = [
    ['① 请求层', '认证、限流、CSRF、可信字段注入', C.navy2, 'E9F1F7'],
    ['② 计划层', '白名单操作与参数格式校验', C.purple, 'EFE9F6'],
    ['③ 风险层', '程序定级与挑战绑定', C.amber, 'FBF1D8'],
    ['④ 授权层', '确认或强认证后的服务端结果', C.red, 'F9E7E5'],
    ['⑤ 执行层', '复检授权与余额、幂等、事务', C.green, 'E8F3EC']
  ];
  securityLayers.forEach((item, index) => {
    const y = 2.12 + index * 0.9;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.91, h: 0.8,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 9.04, y: y + 0.1, w: 1.2, h: 0.2,
      fontSize: 8.8, bold: true, color: item[2], margin: 0
    });
    slide.addText(item[1], {
      x: 9.04, y: y + 0.34, w: 3.5, h: 0.34,
      fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
    });
    if (index < securityLayers.length - 1) {
      slide.addShape(S.line, {
        x: 10.72, y: y + 0.8, w: 0, h: 0.1,
        line: { color: '98A5AF', width: 1, endArrowType: 'triangle' }
      });
    }
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.36, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('模型分类只用于分流与理解，不能替代工具权限；真正的门在代码和服务端', {
    x: 0.93, y: 6.45, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 6.88, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('30', {
    x: 12.55, y: 6.86, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第三十一页：安全总览（下）密钥与数据脱敏
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('SECURITY · OVERVIEW 2/2', {
    x: 0.62, y: 0.42, w: 4.0, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('密钥管理与数据脱敏：没有密钥，就没有越权', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('模型能接触到的每一样东西，都要假设它最终会出现在某个不该出现的地方。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：密钥三条。
  slide.addText('1  密钥的三条铁律', {
    x: 0.62, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const keyRules = [
    {
      title: '① 不进代码仓库', color: C.red, fill: 'F9E7E5',
      desc: '密钥保存在环境变量或密钥管理服务；配置文件里只留占位名，历史提交也不要留真值。'
    },
    {
      title: '② 不进入模型上下文', color: C.amber, fill: 'FBF1D8',
      desc: 'API Key、数据库口令、签名私钥绝不写进 Prompt、工具描述或示例数据。'
    },
    {
      title: '③ 可轮换、最小权限', color: C.navy2, fill: 'E9F1F7',
      desc: '按环境分配不同凭据并定期轮换；给工具的权限只覆盖它需要的那几张表或几个接口。'
    }
  ];
  keyRules.forEach((item, index) => {
    const y = 2.12 + index * 1.44;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 1.32,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 0.84, y: y + 0.12, w: 4.0, h: 0.2,
      fontSize: 9.2, bold: true, color: item.color, margin: 0
    });
    slide.addText(item.desc, {
      x: 0.84, y: y + 0.38, w: 4.0, h: 0.84,
      fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：脱敏规则。
  slide.addText('2  脱敏规则', {
    x: 5.24, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const maskRows = [
    ['卡号', '6222 **** **** 1234', '只留后四位'],
    ['手机号', '138****5678', '中间打码'],
    ['身份证', '3101**********1234', '只留首尾'],
    ['邮箱', 'z***@example.com', '用户名打码'],
    ['交易备注', '按需截断', '可能含隐私']
  ];
  maskRows.forEach((item, index) => {
    const y = 2.12 + index * 0.66;
    slide.addShape(S.roundRect, {
      x: 5.24, y, w: 3.7, h: 0.58,
      rectRadius: 0.03,
      fill: { color: index % 2 === 0 ? 'F6F8FA' : 'FFFFFF' },
      line: { color: 'E1E6EA', width: 0.8 }
    });
    slide.addText(item[0], {
      x: 5.42, y: y + 0.1, w: 0.9, h: 0.18,
      fontSize: 7.6, bold: true, color: C.navy2, margin: 0
    });
    slide.addText(item[1], {
      x: 6.34, y: y + 0.09, w: 1.7, h: 0.18,
      fontFace: 'Consolas', fontSize: 7.0, color: C.ink, margin: 0, fit: 'shrink'
    });
    slide.addText(item[2], {
      x: 8.06, y: y + 0.1, w: 0.78, h: 0.18,
      fontSize: 6.6, color: C.muted, margin: 0, fit: 'shrink'
    });
  });
  slide.addShape(S.roundRect, {
    x: 5.24, y: 5.52, w: 3.7, h: 1.02,
    rectRadius: 0.04,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('脱敏要发生在"进入模型之前"', {
    x: 5.46, y: 5.64, w: 3.3, h: 0.2,
    fontSize: 8.8, bold: true, color: C.purple, margin: 0, fit: 'shrink'
  });
  slide.addText('如果先把完整数据交给模型再要求它别说出去，那已经晚了：数据已进入上下文与日志。', {
    x: 5.46, y: 5.88, w: 3.3, h: 0.6,
    fontSize: 7.4, color: C.ink, margin: 0, fit: 'shrink'
  });

  // 右栏：只能由服务端产生的字段。
  slide.addText('3  只能由服务端产生', {
    x: 8.82, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const serverOnly = [
    ['user_id / account_id', '来自认证 Session，前端与消息都不可声明', C.green, 'E8F3EC'],
    ['risk_level', '由 security_policy 计算，模型无权设定', C.amber, 'FBF1D8'],
    ['authorized', '来自确认或认证服务，不是模型参数', C.red, 'F9E7E5'],
    ['balance', '来自业务系统实时读取，不能由模型背诵', C.navy2, 'E9F1F7'],
    ['operation_hash', '程序生成，用于绑定本次操作参数', C.purple, 'EFE9F6'],
    ['request_id', '服务端生成，参与审计与幂等', C.teal, 'E5F2F0']
  ];
  serverOnly.forEach((item, index) => {
    const y = 2.12 + index * 0.72;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.91, h: 0.64,
      rectRadius: 0.035,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 9.04, y: y + 0.09, w: 3.5, h: 0.18,
      fontFace: 'Consolas', fontSize: 7.8, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 9.04, y: y + 0.29, w: 3.5, h: 0.3,
      fontSize: 7.1, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 5.76, w: 4.42, h: 0.78,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1 }
  });
  slide.addText('日志里也不能有真值', {
    x: 0.84, y: 5.88, w: 4.0, h: 0.18,
    fontSize: 8.6, bold: true, color: C.red, margin: 0
  });
  slide.addText('异常堆栈、调试输出、第三方 APM 上报同样可能泄露敏感字段，要一并过滤。', {
    x: 0.84, y: 6.1, w: 4.0, h: 0.38,
    fontSize: 7.3, color: C.red, margin: 0, fit: 'shrink'
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('31', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第三十二页：RAG 与政策知识库
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('RAG · KNOWLEDGE BASE', {
    x: 0.62, y: 0.42, w: 3.6, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('RAG：政策与产品知识库，管的是"怎么说"', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('知识库回答"规定是什么"，业务 API 回答"我现在有多少钱"；两者不能互相替代。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：三类数据去哪。
  slide.addText('1  三类数据，三个去处', {
    x: 0.62, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const dataRoutes = [
    {
      title: '政策 · FAQ · 产品说明书', color: C.teal, fill: 'E5F2F0',
      desc: '进 RAG 知识库：更新慢、可版本化、需要引用来源。'
    },
    {
      title: '余额 · 交易 · 账户状态', color: C.navy2, fill: 'E9F1F7',
      desc: '走实时业务 API：必须是最新事实，不能靠检索近似。'
    },
    {
      title: '密码 · 验证码 · 密钥', color: C.red, fill: 'F9E7E5',
      desc: '既不进 RAG，也不进模型与日志；只能由认证服务处理。'
    }
  ];
  dataRoutes.forEach((item, index) => {
    const y = 2.12 + index * 1.38;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 1.26,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 0.84, y: y + 0.12, w: 4.0, h: 0.2,
      fontSize: 9.0, bold: true, color: item.color, margin: 0, fit: 'shrink'
    });
    slide.addText(item.desc, {
      x: 0.84, y: y + 0.38, w: 4.0, h: 0.78,
      fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.26, w: 4.42, h: 0.4,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('用一个问题检验：这个答案今天会变吗？', {
    x: 0.84, y: 6.37, w: 4.0, h: 0.18,
    fontSize: 8.0, bold: true, color: C.navy, align: 'center', margin: 0
  });

  // 中栏：向量库选型。
  slide.addText('2  向量库怎么选', {
    x: 5.24, y: 1.72, w: 2.6, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const vectorDbs = [
    {
      name: 'Chroma', color: C.navy2, fill: 'E9F1F7',
      desc: '适合学习与原型：装起来快，本地跑，够用来验证检索效果。'
    },
    {
      name: 'pgvector', color: C.green, fill: 'E8F3EC',
      desc: '适合已有 PostgreSQL 的系统：向量与业务数据同库，能享受事务与 SQL 过滤。'
    },
    {
      name: 'FAISS', color: C.purple, fill: 'EFE9F6',
      desc: '适合高性能定制检索：需要自己维护元数据、权限与更新流程。'
    }
  ];
  vectorDbs.forEach((item, index) => {
    const y = 2.12 + index * 1.28;
    slide.addShape(S.roundRect, {
      x: 5.24, y, w: 3.7, h: 1.16,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.name, {
      x: 5.46, y: y + 0.12, w: 3.3, h: 0.2,
      fontFace: 'Consolas', fontSize: 9.4, bold: true, color: item.color, margin: 0
    });
    slide.addText(item.desc, {
      x: 5.46, y: y + 0.38, w: 3.3, h: 0.7,
      fontSize: 7.5, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 5.24, y: 5.96, w: 3.7, h: 0.7,
    rectRadius: 0.04,
    fill: { color: 'FBF1D8' }, line: { color: C.amber, width: 1 }
  });
  slide.addText('Embedding 只负责找相似文本，不负责判断真假。', {
    x: 5.46, y: 6.1, w: 3.3, h: 0.44,
    fontSize: 7.6, bold: true, color: C.amber, margin: 0, fit: 'shrink'
  });

  // 右栏：metadata 不是权限。
  slide.addText('3  metadata 不是权限', {
    x: 8.82, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 8.82, y: 2.12, w: 3.91, h: 1.9,
    rectRadius: 0.04,
    fill: { color: 'F9E7E5' }, line: { color: 'E7B8B4', width: 1.1 }
  });
  slide.addText('这一页最重要的一条', {
    x: 9.04, y: 2.26, w: 3.5, h: 0.2,
    fontSize: 9.0, bold: true, color: C.red, margin: 0
  });
  slide.addText('向量库里的 tenant_id、user_id 字段只是数据，不是访问控制。把过滤条件交给客户端或模型去填，等于没有权限。', {
    x: 9.04, y: 2.5, w: 3.5, h: 0.86,
    fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
  });
  slide.addText('正确做法：过滤条件由可信认证身份构造，并在 Top-K 候选选择之前生效。', {
    x: 9.04, y: 3.4, w: 3.5, h: 0.5,
    fontSize: 7.6, bold: true, color: C.red, margin: 0, fit: 'shrink'
  });

  const ragRules = [
    ['先过滤，再检索', '越权数据根本不该进入候选集，而不是取回后再筛掉', C.green, 'E8F3EC'],
    ['资料要有版本', '政策会改；回答必须能定位到哪个版本在生效', C.navy2, 'E9F1F7'],
    ['检索不到就直说', '没有命中时不能编造，要明确告知未找到相关规定', C.amber, 'FBF1D8']
  ];
  ragRules.forEach((item, index) => {
    const y = 4.18 + index * 0.84;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.91, h: 0.74,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 9.04, y: y + 0.09, w: 3.5, h: 0.18,
      fontSize: 8.6, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 9.04, y: y + 0.29, w: 3.5, h: 0.38,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 7.1, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('32', {
    x: 12.55, y: 7.08, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第三十三页：RAG 的完整链路与来源标注
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('RAG · PIPELINE', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('RAG 链路：先过滤，再检索，最后带出处回答', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('模型的回答必须能落回具体文件与版本；落不回去的句子，就不该出现在答案里。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：五步链路。
  slide.addText('1  五个步骤', {
    x: 0.62, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const ragPipeline = [
    ['01', '切分与索引', '长文档切块、生成 Embedding、写入向量库', C.navy2, 'E9F1F7'],
    ['02', '按身份过滤', '用可信身份构造 tenant/user 过滤条件', C.red, 'F9E7E5'],
    ['03', '检索 Top-K', '在允许范围内取回候选原文片段', C.purple, 'EFE9F6'],
    ['04', '重排与截断', '按相关度重排，控制上下文长度与成本', C.amber, 'FBF1D8'],
    ['05', '生成并标注来源', '模型只依据原文组织回答，附文件与版本', C.green, 'E8F3EC']
  ];
  ragPipeline.forEach((item, index) => {
    const y = 2.12 + index * 0.82;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 0.72,
      rectRadius: 0.04,
      fill: { color: item[4] }, line: { color: item[3], width: 1 }
    });
    slide.addShape(S.ellipse, {
      x: 0.82, y: y + 0.2, w: 0.3, h: 0.3,
      fill: { color: item[3] }, line: { color: item[3] }
    });
    slide.addText(item[0], {
      x: 0.82, y: y + 0.28, w: 0.3, h: 0.12,
      fontSize: 6.6, bold: true, color: C.white, align: 'center', margin: 0
    });
    slide.addText(item[1], {
      x: 1.24, y: y + 0.11, w: 3.6, h: 0.18,
      fontSize: 8.6, bold: true, color: C.ink, margin: 0, fit: 'shrink'
    });
    slide.addText(item[2], {
      x: 1.24, y: y + 0.33, w: 3.6, h: 0.34,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
    if (index < ragPipeline.length - 1) {
      slide.addShape(S.line, {
        x: 0.97, y: y + 0.72, w: 0, h: 0.1,
        line: { color: '98A5AF', width: 1, endArrowType: 'triangle' }
      });
    }
  });

  // 中栏：回答必须带什么。
  slide.addText('2  一条合格回答带什么', {
    x: 5.24, y: 1.72, w: 3.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  slide.addShape(S.roundRect, {
    x: 5.24, y: 2.12, w: 3.7, h: 1.9,
    rectRadius: 0.04,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1.1 }
  });
  slide.addShape(S.rect, {
    x: 5.24, y: 2.12, w: 3.7, h: 0.4,
    fill: { color: C.navy2 }, line: { color: C.navy2 }
  });
  slide.addText('带来源的检索结果', {
    x: 5.46, y: 2.24, w: 2.4, h: 0.18,
    fontSize: 8.8, bold: true, color: C.white, margin: 0
  });
  slide.addText('{\n  "answer": "个人账户单笔\n     转账上限为五万元。",\n  "sources": [\n    {"doc": "个人转账\n      业务规则",\n     "version": "v3.2",\n     "effective": "2026-07-01",\n     "chunk": "§2.1"}\n  ]\n}', {
    x: 5.46, y: 2.6, w: 3.3, h: 1.34,
    fontFace: 'Consolas', fontSize: 6.8, color: C.ink,
    margin: 0, valign: 'top', fit: 'shrink'
  });

  const answerRules = [
    ['必须有出处', '每个结论都能对应到文件与版本', C.green, 'E8F3EC'],
    ['版本要能对上', '政策已更新时不能引用旧版本', C.amber, 'FBF1D8'],
    ['无依据不回答', '检索为空时明确说明未找到，而不是顺口编一个', C.red, 'F9E7E5']
  ];
  answerRules.forEach((item, index) => {
    const y = 4.18 + index * 0.84;
    slide.addShape(S.roundRect, {
      x: 5.24, y, w: 3.7, h: 0.74,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 5.46, y: y + 0.09, w: 3.3, h: 0.18,
      fontSize: 8.6, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 5.46, y: y + 0.29, w: 3.3, h: 0.38,
      fontSize: 7.2, color: C.muted, margin: 0, fit: 'shrink'
    });
  });

  // 右栏：三种方式对比。
  slide.addText('3  为什么不能只靠模型或关键词', {
    x: 8.82, y: 1.72, w: 3.8, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const compareRows = [
    ['只用模型', '知识可能过期，无法追溯到依据', C.red, 'F9E7E5'],
    ['只用关键词', '说法一变就搜不到，政策表述往往不统一', C.amber, 'FBF1D8'],
    ['RAG', '语义召回 + 原文引用，且资料可独立更新', C.green, 'E8F3EC']
  ];
  compareRows.forEach((item, index) => {
    const y = 2.12 + index * 1.0;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.91, h: 0.9,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 9.04, y: y + 0.12, w: 3.5, h: 0.2,
      fontSize: 9.2, bold: true, color: item[2], margin: 0
    });
    slide.addText(item[1], {
      x: 9.04, y: y + 0.38, w: 3.5, h: 0.44,
      fontSize: 7.5, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 8.82, y: 5.12, w: 3.91, h: 1.54,
    rectRadius: 0.04,
    fill: { color: 'EFE9F6' }, line: { color: C.purple, width: 1 }
  });
  slide.addText('RAG 在银行 Agent 里用于', {
    x: 9.04, y: 5.26, w: 3.5, h: 0.2,
    fontSize: 8.8, bold: true, color: C.purple, margin: 0
  });
  slide.addText('· 政策与限额规定的解释\n· 产品说明书要点\n· 常见问题与办理指引\n· 费率与期限口径说明', {
    x: 9.04, y: 5.5, w: 3.5, h: 1.06,
    fontSize: 7.5, color: C.ink, margin: 0, fit: 'shrink'
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.32, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('知识库管"规定怎么写的"，业务 API 管"你现在什么状态"；两者混用就会出错', {
    x: 0.93, y: 6.41, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 6.88, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('33', {
    x: 12.55, y: 6.86, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

// 第三十四页：收尾，知识地图与下一步
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('CLOSING', {
    x: 0.62, y: 0.42, w: 3.2, h: 0.2,
    fontSize: 9, bold: true, color: C.teal, margin: 0
  });
  slide.addText('回到全景：这套系统由什么构成、还差什么', {
    x: 0.62, y: 0.72, w: 11.8, h: 0.48,
    fontSize: 23, bold: true, color: C.ink, margin: 0
  });
  slide.addText('前 16 页讲机制，中间 8 页讲场景工具，最后 9 页讲支撑体系；这一页把它们合起来看。', {
    x: 0.62, y: 1.25, w: 11.8, h: 0.28,
    fontSize: 11, color: C.muted, margin: 0
  });

  // 左栏：三次递进。
  slide.addText('1  三次递进', {
    x: 0.62, y: 1.72, w: 2.2, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const recap = [
    {
      title: '一 · 机制（第 8–16 页）', color: C.purple, fill: 'EFE9F6',
      desc: '用转账这一条主线，把 State、节点、条件边、interrupt、Checkpoint、resume 全部走一遍。目的是能自己画出图。'
    },
    {
      title: '二 · 场景工具（第 17–24 页）', color: C.amber, fill: 'FBF1D8',
      desc: '六个场景各需要哪些工具、什么风险等级、哪些工具不能给模型；复杂度越高，页数越多。'
    },
    {
      title: '三 · 支撑体系（第 25–33 页）', color: C.teal, fill: 'E5F2F0',
      desc: '数据、持久化、幂等、审计、安全、RAG；这些不直接产出功能，但决定系统能不能上生产。'
    }
  ];
  recap.forEach((item, index) => {
    const y = 2.12 + index * 1.44;
    slide.addShape(S.roundRect, {
      x: 0.62, y, w: 4.42, h: 1.32,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 0.84, y: y + 0.12, w: 4.0, h: 0.2,
      fontSize: 9.2, bold: true, color: item.color, margin: 0, fit: 'shrink'
    });
    slide.addText(item.desc, {
      x: 0.84, y: y + 0.38, w: 4.0, h: 0.84,
      fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 中栏：还差什么。
  slide.addText('2  还差什么才算能跑', {
    x: 5.24, y: 1.72, w: 3.0, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const gaps = [
    ['已实现', '转账主线的教学版工作流与 11 条测试', C.green, 'E8F3EC'],
    ['待实现 · 高优先级', '真实模型接入、多轮槽位合并、真实认证与身份注入', C.red, 'F9E7E5'],
    ['待实现 · 中优先级', '其余五个场景的工具与业务规则、模拟数据流水线', C.amber, 'FBF1D8'],
    ['待实现 · 收尾', '持久化 Checkpointer、审计落库、幂等约束、前端真做', C.navy2, 'E9F1F7'],
    ['尚未冻结', '接口与事件契约、领域模型、风险阈值、验收边界', C.purple, 'EFE9F6']
  ];
  gaps.forEach((item, index) => {
    const y = 2.12 + index * 1.0;
    slide.addShape(S.roundRect, {
      x: 5.24, y, w: 3.7, h: 0.9,
      rectRadius: 0.04,
      fill: { color: item[3] }, line: { color: item[2], width: 1 }
    });
    slide.addText(item[0], {
      x: 5.46, y: y + 0.12, w: 3.3, h: 0.18,
      fontSize: 8.6, bold: true, color: item[2], margin: 0, fit: 'shrink'
    });
    slide.addText(item[1], {
      x: 5.46, y: y + 0.34, w: 3.3, h: 0.5,
      fontSize: 7.3, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  // 右栏：三条主线结论。
  slide.addText('3  三条结论', {
    x: 8.82, y: 1.72, w: 2.4, h: 0.28,
    fontSize: 14, bold: true, color: C.ink, margin: 0
  });
  const conclusions = [
    {
      title: '模型只做理解与表达', color: C.purple, fill: 'EFE9F6',
      desc: '它输出候选意图和候选参数，不负责证明身份，也不能决定资金是否获准。'
    },
    {
      title: '程序负责判定与执行', color: C.amber, fill: 'FBF1D8',
      desc: '白名单、风险等级、挑战绑定、幂等与审计都由确定性代码完成，可测试、可复现。'
    },
    {
      title: '后端才是真实状态', color: C.green, fill: 'E8F3EC',
      desc: '余额、交易与账户状态只来自业务系统；Checkpoint 与知识库都不是账本。'
    }
  ];
  conclusions.forEach((item, index) => {
    const y = 2.12 + index * 1.32;
    slide.addShape(S.roundRect, {
      x: 8.82, y, w: 3.91, h: 1.2,
      rectRadius: 0.04,
      fill: { color: item.fill }, line: { color: item.color, width: 1 }
    });
    slide.addText(item.title, {
      x: 9.04, y: y + 0.12, w: 3.5, h: 0.2,
      fontSize: 9.2, bold: true, color: item.color, margin: 0
    });
    slide.addText(item.desc, {
      x: 9.04, y: y + 0.38, w: 3.5, h: 0.72,
      fontSize: 7.6, color: C.ink, margin: 0, fit: 'shrink'
    });
  });

  slide.addShape(S.roundRect, {
    x: 8.82, y: 6.1, w: 3.91, h: 0.5,
    rectRadius: 0.04,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText('LLM 提议 · Python 决策 · 后端执行', {
    x: 9.04, y: 6.24, w: 3.5, h: 0.2,
    fontSize: 9.0, bold: true, color: C.white, align: 'center', margin: 0
  });

  slide.addShape(S.roundRect, {
    x: 0.62, y: 6.4, w: 12.11, h: 0.34,
    rectRadius: 0.035,
    fill: { color: 'FFFFFF' }, line: { color: 'C8D4DE', width: 1 }
  });
  slide.addText('讨论入口：先定接口与事件契约，再并行推进五个场景的工具与数据准备', {
    x: 0.93, y: 6.49, w: 11.5, h: 0.15,
    fontSize: 8.4, bold: true, color: C.navy, align: 'center', margin: 0
  });

  slide.addText('银行 AI 智能体 · 全流程规划', {
    x: 0.62, y: 6.88, w: 3.6, h: 0.14,
    fontSize: 7.5, color: C.muted, margin: 0
  });
  slide.addText('34', {
    x: 12.55, y: 6.86, w: 0.25, h: 0.16,
    fontSize: 8, color: C.muted, align: 'right', margin: 0
  });
}

pptx.writeFile({ fileName: '银行AI智能体全流程规划.pptx' });
