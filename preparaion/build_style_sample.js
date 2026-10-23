const pptxgen = require('../../.dsh/pptx-tools/node_modules/pptxgenjs');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = '有度 YouDu';
pptx.subject = '有度 · 银行 AI 智能体全流程规划风格样稿';
pptx.title = '有度 · 银行 AI 智能体全流程规划';
pptx.company = '有度 YouDu';
pptx.lang = 'zh-CN';
pptx.theme = {
  headFontFace: 'Microsoft YaHei',
  bodyFontFace: 'Microsoft YaHei',
  lang: 'zh-CN'
};
pptx.defineSlideMaster({
  title: 'CONTENT',
  background: { color: 'F5F7F9' },
  objects: [
    { rect: { x: 0, y: 0, w: 13.333, h: 0.12, fill: { color: '173B5E' }, line: { color: '173B5E' } } },
    { text: { text: '有度 · 银行 AI 智能体 · 全流程规划', options: { x: 0.55, y: 7.13, w: 4.2, h: 0.16, fontFace: 'Microsoft YaHei', fontSize: 8, color: '6D7A86', margin: 0 } } },
    { text: { text: '内部启动会', options: { x: 11.65, y: 7.13, w: 1.05, h: 0.16, fontFace: 'Microsoft YaHei', fontSize: 8, color: '6D7A86', align: 'right', margin: 0 } } },
  ],
  slideNumber: { x: 12.78, y: 7.12, w: 0.25, h: 0.16, fontFace: 'Microsoft YaHei', fontSize: 8, color: '6D7A86', align: 'right', margin: 0 }
});

const C = {
  navy: '173B5E', navy2: '244F73', teal: '178078', green: '2F8F63',
  amber: 'E2A62B', red: 'C94F48', purple: '7657A6', ink: '162534',
  muted: '64727F', line: 'D7DEE4', bg: 'F5F7F9', white: 'FFFFFF', softBlue: 'E9F1F7',
  softTeal: 'E5F2F0', softAmber: 'FBF1D8', softRed: 'F9E7E5', softPurple: 'EFE9F6'
};
const S = pptx.ShapeType;

function addTitle(slide, eyebrow, title, subtitle) {
  slide.addText(eyebrow, { x: 0.62, y: 0.42, w: 3.0, h: 0.2, fontSize: 9, bold: true, color: C.teal, charSpacing: 0, margin: 0 });
  slide.addText(title, { x: 0.62, y: 0.72, w: 11.8, h: 0.48, fontSize: 25, bold: true, color: C.ink, margin: 0, breakLine: false });
  if (subtitle) slide.addText(subtitle, { x: 0.62, y: 1.26, w: 11.8, h: 0.28, fontSize: 11, color: C.muted, margin: 0 });
}
function pill(slide, text, x, y, w, fill, color) {
  slide.addShape(S.roundRect, { x, y, w, h: 0.34, rectRadius: 0.06, fill: { color: fill }, line: { color: fill } });
  slide.addText(text, { x, y: y + 0.01, w, h: 0.28, fontSize: 9, bold: true, color, align: 'center', valign: 'mid', margin: 0 });
}
function line(slide, x1, y1, x2, y2, color = C.line, width = 1.2, beginArrowType, endArrowType) {
  slide.addShape(S.line, { x: x1, y: y1, w: x2 - x1, h: y2 - y1, line: { color, width, beginArrowType, endArrowType } });
}
function node(slide, {x,y,w,h,title,body,fill=C.white,stroke=C.line,accent=C.teal,num}) {
  slide.addShape(S.roundRect, { x, y, w, h, rectRadius: 0.05, fill: { color: fill }, line: { color: stroke, width: 1.2 } });
  slide.addShape(S.rect, { x, y, w: 0.07, h, fill: { color: accent }, line: { color: accent } });
  if (num) {
    slide.addShape(S.ellipse, { x: x + 0.18, y: y + 0.2, w: 0.38, h: 0.38, fill: { color: accent }, line: { color: accent } });
    slide.addText(String(num), { x: x + 0.18, y: y + 0.235, w: 0.38, h: 0.2, fontSize: 9, bold: true, color: C.white, align: 'center', margin: 0 });
  }
  const tx = x + (num ? 0.68 : 0.22);
  slide.addText(title, { x: tx, y: y + 0.18, w: w - (num ? 0.86 : 0.42), h: 0.26, fontSize: 13, bold: true, color: C.ink, margin: 0, fit: 'shrink' });
  slide.addText(body, { x: x + 0.22, y: y + 0.62, w: w - 0.44, h: h - 0.78, fontSize: 9.5, color: C.muted, breakLine: false, margin: 0, valign: 'top', fit: 'shrink' });
}

// 1. 封面
{
  const slide = pptx.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(S.rect, { x: 0, y: 0, w: 4.0, h: 7.5, fill: { color: C.navy }, line: { color: C.navy } });
  slide.addShape(S.rect, { x: 0.56, y: 0.72, w: 0.52, h: 0.07, fill: { color: C.teal }, line: { color: C.teal } });
  slide.addText('YOUDU · BANKING AGENT', { x: 0.56, y: 0.92, w: 2.7, h: 0.28, fontSize: 11, bold: true, color: 'BFD2E1', charSpacing: 1.4, margin: 0 });
  slide.addText('安全可信的\n自主执行', { x: 0.56, y: 1.7, w: 2.9, h: 1.3, fontSize: 29, bold: true, color: C.white, breakLine: false, margin: 0, valign: 'mid' });
  slide.addText('LLM 提议 · Python 决策 · 银行后端执行', { x: 0.56, y: 3.28, w: 2.85, h: 0.6, fontSize: 11, color: 'D7E4EC', margin: 0, breakLine: false });
  const risks = [
    ['绿色', C.green], ['黄色', C.amber], ['红色', C.red]
  ];
  risks.forEach((r, i) => {
    slide.addShape(S.ellipse, { x: 0.58 + i * 0.88, y: 5.9, w: 0.18, h: 0.18, fill: { color: r[1] }, line: { color: r[1] } });
    slide.addText(r[0], { x: 0.82 + i * 0.88, y: 5.87, w: 0.5, h: 0.22, fontSize: 9, color: C.white, margin: 0 });
  });
  slide.addText('有度', { x: 4.75, y: 1.32, w: 7.4, h: 0.62, fontSize: 40, bold: true, color: C.ink, margin: 0, breakLine: false });
  slide.addText('银行 AI 智能体全流程规划', { x: 4.78, y: 1.98, w: 7.4, h: 0.45, fontSize: 19, bold: true, color: C.ink, margin: 0, breakLine: false });
  slide.addText('团队内部启动会 · 风格样稿', { x: 4.78, y: 2.9, w: 4.8, h: 0.34, fontSize: 15, color: C.teal, bold: true, margin: 0 });
  slide.addText('从自然语言交互，到可审计、可验证、可恢复的银行业务执行。', { x: 4.78, y: 3.5, w: 6.9, h: 0.5, fontSize: 14, color: C.muted, margin: 0 });
  line(slide, 4.78, 4.45, 11.9, 4.45, C.line, 1);
  slide.addText('产品范围', { x: 4.78, y: 4.75, w: 1.2, h: 0.25, fontSize: 9, bold: true, color: C.muted, margin: 0 });
  slide.addText('转账 · 账单 · 理财 · 卡片 · 订阅 · 跨场景联动', { x: 4.78, y: 5.12, w: 7.4, h: 0.36, fontSize: 13, color: C.ink, margin: 0 });
  slide.addText('V0.1  |  项目启动前规划', { x: 4.78, y: 6.45, w: 3.5, h: 0.22, fontSize: 9, color: C.muted, margin: 0 });
}

// 2. 章节过渡页
{
  const slide = pptx.addSlide();
  slide.background = { color: C.navy };
  slide.addText('01', { x: 0.72, y: 0.58, w: 1.4, h: 0.9, fontSize: 46, bold: true, color: C.teal, margin: 0 });
  slide.addShape(S.rect, { x: 0.74, y: 1.52, w: 0.72, h: 0.06, fill: { color: C.teal }, line: { color: C.teal } });
  slide.addText('从对话，到可信执行', { x: 0.72, y: 2.0, w: 7.8, h: 0.72, fontSize: 34, bold: true, color: C.white, margin: 0 });
  slide.addText('这一章回答：系统如何理解、判断并安全地完成银行业务？', { x: 0.75, y: 2.95, w: 7.5, h: 0.4, fontSize: 15, color: 'C9D8E3', margin: 0 });
  const labels = [
    ['理解', '自然语言与上下文', C.softBlue, '7DA9C8'],
    ['决策', '权限与风险策略', C.softAmber, C.amber],
    ['执行', '可信业务服务', C.softTeal, C.teal],
    ['追溯', '审计与恢复', C.softPurple, C.purple]
  ];
  labels.forEach((it, i) => {
    const x = 0.75 + i * 3.02;
    slide.addShape(S.roundRect, { x, y: 5.08, w: 2.56, h: 1.18, rectRadius: 0.05, fill: { color: '21496A' }, line: { color: '3C6483', width: 1 } });
    slide.addText(it[0], { x: x + 0.2, y: 5.31, w: 0.7, h: 0.3, fontSize: 13, bold: true, color: it[3], margin: 0 });
    slide.addText(it[1], { x: x + 0.2, y: 5.74, w: 2.1, h: 0.25, fontSize: 10, color: 'D7E4EC', margin: 0 });
  });
  slide.addText('有度 · 内部启动会 · 风格样稿', { x: 0.75, y: 7.05, w: 3.2, h: 0.18, fontSize: 8, color: '93ADC1', margin: 0 });
}

// 3. 架构内容页
{
  const slide = pptx.addSlide('CONTENT');
  addTitle(slide, 'SYSTEM FLOW', '从自然语言到可信执行', '模型负责理解与提议，程序负责授权与执行；每一次状态变化都有证据。');
  const items = [
    ['接入', '登录会话\n请求校验与限流', C.softBlue, '6C9FC2'],
    ['理解', '意图识别\n实体解析与澄清', C.softBlue, C.navy2],
    ['规划', 'LangGraph\n计划与 Checkpoint', C.softBlue, C.teal],
    ['决策', '绿色 / 黄色 / 红色\n确认与强认证', C.softAmber, C.amber],
    ['执行', '业务复检\n事务、幂等与证据', C.softTeal, C.green]
  ];
  const y = 2.08, w = 2.14, gap = 0.3;
  items.forEach((it, i) => {
    const x = 0.64 + i * (w + gap);
    node(slide, { x, y, w, h: 2.15, title: it[0], body: it[1], fill: it[2], stroke: it[3], accent: it[3], num: i + 1 });
    if (i < items.length - 1) line(slide, x + w + 0.03, y + 1.08, x + w + gap - 0.03, y + 1.08, C.muted, 1.4, undefined, 'triangle');
  });
  slide.addShape(S.roundRect, { x: 0.64, y: 4.72, w: 12.05, h: 1.28, rectRadius: 0.04, fill: { color: C.white }, line: { color: C.line, width: 1 } });
  slide.addText('横向能力', { x: 0.88, y: 4.95, w: 1.05, h: 0.27, fontSize: 11, bold: true, color: C.ink, margin: 0 });
  const horiz = [
    ['审计日志', C.purple, C.softPurple], ['异常熔断', C.red, C.softRed], ['人工接管', C.amber, C.softAmber], ['结构化证据', C.teal, C.softTeal]
  ];
  horiz.forEach((it, i) => pill(slide, it[0], 2.18 + i * 2.25, 4.9, 1.75, it[2], it[1]));
  slide.addText('设计原则：任何 Prompt、前端参数或模型输出，都不能绕过确定性安全层直接修改业务状态。', { x: 0.88, y: 5.52, w: 10.8, h: 0.26, fontSize: 10.5, color: C.muted, margin: 0 });
}

// 4. 场景矩阵页
{
  const slide = pptx.addSlide('CONTENT');
  addTitle(slide, 'SCENARIO MAP', '六类场景，共享一套安全底座', '场景复杂度不同，但身份、权限、审计、证据与恢复机制保持统一。');
  const rows = [
    ['账单分析', 2.0, '统计 · 分类 · 异常', '绿色为主', C.green],
    ['订阅管理', 2.5, '周期识别 · 取消', '绿 / 黄', C.teal],
    ['卡片管理', 3.0, '限制 · 状态机 · 挂失', '绿 / 黄 / 红', C.amber],
    ['智能转账', 4.0, '联系人 · 授权 · 幂等', '黄 / 红', C.red],
    ['理财操作', 4.5, '风险画像 · 适当性', '绿 / 黄 / 红', C.purple],
    ['跨场景联动', 5.0, 'DAG · 定时 · 补偿', '动态判级', C.navy]
  ];
  const top = 1.88;
  slide.addText('场景', { x: 0.72, y: top, w: 1.5, h: 0.22, fontSize: 9, bold: true, color: C.muted, margin: 0 });
  slide.addText('复杂度', { x: 2.45, y: top, w: 3.65, h: 0.22, fontSize: 9, bold: true, color: C.muted, margin: 0 });
  slide.addText('关键能力', { x: 6.55, y: top, w: 2.6, h: 0.22, fontSize: 9, bold: true, color: C.muted, margin: 0 });
  slide.addText('主要权限', { x: 10.33, y: top, w: 1.5, h: 0.22, fontSize: 9, bold: true, color: C.muted, margin: 0 });
  rows.forEach((r, i) => {
    const y = 2.26 + i * 0.68;
    slide.addShape(S.line, { x: 0.7, y: y + 0.48, w: 11.9, h: 0, line: { color: C.line, width: 0.8 } });
    slide.addShape(S.ellipse, { x: 0.76, y: y + 0.07, w: 0.18, h: 0.18, fill: { color: r[4] }, line: { color: r[4] } });
    slide.addText(r[0], { x: 1.05, y, w: 1.2, h: 0.3, fontSize: 12, bold: true, color: C.ink, margin: 0 });
    slide.addShape(S.roundRect, { x: 2.45, y: y + 0.05, w: 3.6, h: 0.22, rectRadius: 0.04, fill: { color: 'E6EBEF' }, line: { color: 'E6EBEF' } });
    slide.addShape(S.roundRect, { x: 2.45, y: y + 0.05, w: 3.6 * r[1] / 5, h: 0.22, rectRadius: 0.04, fill: { color: r[4] }, line: { color: r[4] } });
    slide.addText(r[1].toFixed(1) + ' / 5', { x: 5.38, y: y - 0.01, w: 0.64, h: 0.24, fontSize: 9, bold: true, color: C.ink, align: 'right', margin: 0 });
    slide.addText(r[2], { x: 6.55, y, w: 3.2, h: 0.28, fontSize: 11, color: C.ink, margin: 0 });
    slide.addText(r[3], { x: 10.33, y, w: 1.65, h: 0.28, fontSize: 10, bold: true, color: r[4], margin: 0 });
  });
  slide.addShape(S.roundRect, { x: 0.72, y: 6.48, w: 11.92, h: 0.42, rectRadius: 0.04, fill: { color: C.softBlue }, line: { color: 'BFD2E1' } });
  slide.addText('实现策略：先建设共享底座，再按“账单 → 转账 → 订阅/卡片 → 理财 → 跨场景”逐层增加领域能力。', { x: 0.95, y: 6.58, w: 11.3, h: 0.2, fontSize: 10, bold: true, color: C.navy, margin: 0 });
}

// 5. 四周路线图
{
  const slide = pptx.addSlide('CONTENT');
  addTitle(slide, 'DELIVERY ROADMAP', '四周形成可演示、可验证的完整闭环', '范围保持不减；通过纵向切片、接口冻结和提前测试控制风险。');
  const weeks = [
    ['第 1 周', '纵向骨架', ['数据模型与种子', 'React / FastAPI', '余额查询', '小额转账确认'], C.navy2, C.softBlue],
    ['第 2 周', '六场景覆盖', ['领域服务', '业务卡片', '风险画像', '跨场景 DAG'], C.teal, C.softTeal],
    ['第 3 周', '可信执行', ['强认证', '事务与幂等', '熔断与恢复', '审计回放'], C.amber, C.softAmber],
    ['第 4 周', '冻结与交付', ['全量测试', '离线降级', '文档与视频', '计时彩排'], C.purple, C.softPurple]
  ];
  line(slide, 1.2, 2.25, 12.05, 2.25, C.line, 2);
  weeks.forEach((w, i) => {
    const x = 0.68 + i * 3.08;
    slide.addShape(S.ellipse, { x: x + 1.12, y: 2.05, w: 0.4, h: 0.4, fill: { color: w[4] }, line: { color: C.white, width: 2 } });
    slide.addShape(S.roundRect, { x, y: 2.75, w: 2.72, h: 2.65, rectRadius: 0.05, fill: { color: C.white }, line: { color: C.line, width: 1 } });
    slide.addShape(S.rect, { x, y: 2.75, w: 2.72, h: 0.11, fill: { color: w[4] }, line: { color: w[4] } });
    slide.addText(w[0], { x: x + 0.22, y: 3.04, w: 0.72, h: 0.25, fontSize: 10, bold: true, color: w[4], margin: 0 });
    slide.addText(w[1], { x: x + 0.22, y: 3.41, w: 2.15, h: 0.32, fontSize: 16, bold: true, color: C.ink, margin: 0 });
    w[2].forEach((item, j) => {
      slide.addShape(S.ellipse, { x: x + 0.24, y: 4.02 + j * 0.31, w: 0.09, h: 0.09, fill: { color: w[4] }, line: { color: w[4] } });
      slide.addText(item, { x: x + 0.43, y: 3.94 + j * 0.31, w: 1.9, h: 0.21, fontSize: 9.5, color: C.muted, margin: 0 });
    });
  });
  slide.addText('关键门槛', { x: 0.72, y: 5.86, w: 0.9, h: 0.24, fontSize: 10, bold: true, color: C.ink, margin: 0 });
  const gates = ['首周可演示', '第二周接口冻结', '第三周安全测试', '第四周禁止新增功能'];
  gates.forEach((g, i) => pill(slide, g, 1.7 + i * 2.72, 5.8, 2.25, i === 3 ? C.softRed : C.softBlue, i === 3 ? C.red : C.navy));
  slide.addText('完成定义：六场景闭环 + 三级权限不可绕过 + 重复扣款为 0 + 所有成功均有结构化证据。', { x: 0.72, y: 6.55, w: 11.8, h: 0.26, fontSize: 10.5, bold: true, color: C.ink, margin: 0 });
}

pptx.writeFile({ fileName: '有度-银行AI智能体风格样稿.pptx' });
