const fs = require('fs');
const path = require('path');
const pptxgen = require('../../.dsh/pptx-tools/node_modules/pptxgenjs');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'Banking Agent Project';
pptx.title = '银行 Agent 前端工作台预览';
pptx.lang = 'zh-CN';
pptx.theme = { headFontFace: 'Microsoft YaHei', bodyFontFace: 'Microsoft YaHei', lang: 'zh-CN' };

const C = {
  navy: '173B5E', navy2: '244F73', teal: '178078', green: '2F8F63',
  amber: 'E2A62B', red: 'C94F48', purple: '7657A6', ink: '162534',
  muted: '64727F', line: 'D7DEE4', bg: 'EEF2F5', white: 'FFFFFF',
  softBlue: 'E9F1F7', softTeal: 'E5F2F0', softAmber: 'FBF1D8', softRed: 'F9E7E5'
};
const S = pptx.ShapeType;
const iconRoot = path.resolve(__dirname, '../../.dsh/pptx-tools/node_modules/lucide-static/icons');

function iconData(name, color) {
  const svg = fs.readFileSync(path.join(iconRoot, name + '.svg'), 'utf8')
    .replace(/currentColor/g, '#' + color)
    .replace(/<!--.*?-->/gs, '');
  return 'data:image/svg+xml;base64,' + Buffer.from(svg).toString('base64');
}
function addIcon(slide, name, x, y, w, h, color) {
  slide.addImage({ data: iconData(name, color), x, y, w, h });
}
function text(slide, value, x, y, w, h, size, color, bold = false, align = 'left') {
  slide.addText(value, { x, y, w, h, fontSize: size, color, bold, align, margin: 0, valign: 'mid', fit: 'shrink' });
}
function rounded(slide, x, y, w, h, fill, line = fill, radius = 0.04) {
  slide.addShape(S.roundRect, { x, y, w, h, rectRadius: radius, fill: { color: fill }, line: { color: line, width: 1 } });
}

const slide = pptx.addSlide();
slide.background = { color: C.bg };

// 应用外框
rounded(slide, 0.18, 0.16, 12.97, 7.16, C.white, 'CDD6DE', 0.06);

// 顶部栏
slide.addShape(S.rect, { x: 0.19, y: 0.17, w: 12.95, h: 0.66, fill: { color: C.white }, line: { color: C.white } });
slide.addShape(S.line, { x: 0.19, y: 0.83, w: 12.95, h: 0, line: { color: C.line, width: 0.8 } });
rounded(slide, 0.45, 0.32, 0.34, 0.34, C.navy, C.navy, 0.05);
addIcon(slide, 'shield-check', 0.53, 0.40, 0.18, 0.18, C.white);
text(slide, '智银 Agent', 0.92, 0.31, 1.25, 0.32, 14, C.ink, true);
rounded(slide, 2.22, 0.34, 0.76, 0.28, C.softTeal, C.softTeal, 0.04);
slide.addShape(S.ellipse, { x: 2.34, y: 0.435, w: 0.08, h: 0.08, fill: { color: C.green }, line: { color: C.green } });
text(slide, '服务正常', 2.46, 0.37, 0.48, 0.17, 7.5, C.green, true);
addIcon(slide, 'search', 10.66, 0.39, 0.19, 0.19, C.muted);
addIcon(slide, 'clock-3', 11.18, 0.39, 0.19, 0.19, C.muted);
slide.addShape(S.ellipse, { x: 11.82, y: 0.29, w: 0.4, h: 0.4, fill: { color: C.navy2 }, line: { color: C.navy2 } });
text(slide, '林', 11.82, 0.39, 0.4, 0.15, 9, C.white, true, 'center');
text(slide, '林晓', 12.32, 0.32, 0.52, 0.3, 10, C.ink, true);

// 左侧栏
slide.addShape(S.rect, { x: 0.19, y: 0.84, w: 2.2, h: 6.47, fill: { color: 'F7F9FB' }, line: { color: 'F7F9FB' } });
slide.addShape(S.line, { x: 2.39, y: 0.84, w: 0, h: 6.47, line: { color: C.line, width: 0.8 } });
text(slide, '账户概览', 0.47, 1.06, 1.2, 0.25, 10, C.muted, true);
rounded(slide, 0.42, 1.43, 1.76, 1.17, C.navy, C.navy, 0.05);
text(slide, '可用余额', 0.63, 1.62, 0.72, 0.2, 8.5, 'BDD0DF');
text(slide, '¥ 18,600.00', 0.63, 1.94, 1.42, 0.3, 17, C.white, true);
text(slide, '储蓄卡 · 尾号 1024', 0.63, 2.35, 1.25, 0.16, 8, 'C9D8E3');

const nav = [
  ['message-circle', 'AI 助理', true],
  ['receipt', '账单分析', false],
  ['circle-dollar-sign', '转账汇款', false],
  ['chart-no-axes-combined', '理财中心', false],
  ['credit-card', '卡片管理', false]
];
nav.forEach((item, index) => {
  const y = 2.95 + index * 0.54;
  if (item[2]) rounded(slide, 0.4, y - 0.07, 1.78, 0.43, C.softBlue, C.softBlue, 0.035);
  addIcon(slide, item[0], 0.58, y, 0.2, 0.2, item[2] ? C.navy : C.muted);
  text(slide, item[1], 0.92, y - 0.01, 0.88, 0.22, 9.5, item[2] ? C.navy : C.muted, item[2]);
  if (item[2]) slide.addShape(S.rect, { x: 0.4, y: y - 0.07, w: 0.05, h: 0.43, fill: { color: C.teal }, line: { color: C.teal } });
});
text(slide, '快捷操作', 0.47, 5.86, 1.0, 0.22, 9, C.muted, true);
rounded(slide, 0.43, 6.22, 0.78, 0.45, C.white, C.line, 0.035);
rounded(slide, 1.31, 6.22, 0.78, 0.45, C.white, C.line, 0.035);
text(slide, '查余额', 0.43, 6.35, 0.78, 0.18, 8.5, C.ink, true, 'center');
text(slide, '查账单', 1.31, 6.35, 0.78, 0.18, 8.5, C.ink, true, 'center');

// 中央对话区
slide.addShape(S.rect, { x: 2.4, y: 0.84, w: 7.45, h: 6.47, fill: { color: C.white }, line: { color: C.white } });
text(slide, '智能助理', 2.75, 1.03, 1.2, 0.3, 15, C.ink, true);
text(slide, '当前会话 · 日常财务', 7.55, 1.06, 1.7, 0.22, 8.5, C.muted, false, 'right');
slide.addShape(S.line, { x: 2.4, y: 1.46, w: 7.45, h: 0, line: { color: 'E8EDF1', width: 0.8 } });

rounded(slide, 2.76, 1.74, 4.65, 0.56, 'F3F6F8', 'F3F6F8', 0.05);
text(slide, '上午好，林晓。今天想查询还是办理业务？', 3.0, 1.9, 4.15, 0.22, 10, C.ink);

rounded(slide, 5.25, 2.56, 4.2, 0.63, C.navy, C.navy, 0.05);
text(slide, '分析我这个月的消费，顺便给张伟转 300 元。', 5.52, 2.75, 3.65, 0.24, 10, C.white);

// 账单分析卡
rounded(slide, 2.76, 3.48, 3.15, 2.15, C.white, C.line, 0.045);
addIcon(slide, 'receipt', 2.98, 3.72, 0.22, 0.22, C.teal);
text(slide, '本月消费分析', 3.32, 3.67, 1.45, 0.3, 12, C.ink, true);
text(slide, '总支出', 3.0, 4.14, 0.65, 0.2, 8, C.muted);
text(slide, '¥ 6,482', 3.0, 4.39, 1.1, 0.28, 17, C.ink, true);
const bars = [
  ['餐饮', 0.74, C.teal, '¥2,180'],
  ['居住', 0.58, C.navy2, '¥1,800'],
  ['交通', 0.31, C.amber, '¥760']
];
bars.forEach((item, index) => {
  const y = 4.78 + index * 0.25;
  text(slide, item[0], 4.17, y - 0.02, 0.4, 0.16, 7.5, C.muted);
  rounded(slide, 4.62, y, 0.72, 0.09, 'E8EDF1', 'E8EDF1', 0.02);
  rounded(slide, 4.62, y, 0.72 * item[1], 0.09, item[2], item[2], 0.02);
  text(slide, item[3], 5.39, y - 0.04, 0.4, 0.16, 7, C.muted, false, 'right');
});
rounded(slide, 2.98, 5.29, 2.65, 0.24, C.softRed, C.softRed, 0.03);
slide.addShape(S.ellipse, { x: 3.1, y: 5.375, w: 0.07, h: 0.07, fill: { color: C.red }, line: { color: C.red } });
text(slide, '发现 1 笔疑似重复订阅扣款', 3.25, 5.34, 2.16, 0.14, 7.5, C.red, true);

// 转账确认卡
rounded(slide, 6.16, 3.48, 3.29, 2.15, C.softAmber, 'E8C76F', 0.045);
addIcon(slide, 'shield-check', 6.39, 3.7, 0.23, 0.23, C.amber);
text(slide, '转账需要确认', 6.74, 3.67, 1.5, 0.3, 12, C.ink, true);
rounded(slide, 8.52, 3.7, 0.66, 0.25, 'F6DC97', 'F6DC97', 0.03);
text(slide, '黄色', 8.52, 3.765, 0.66, 0.12, 7.5, '8A6212', true, 'center');
text(slide, '收款人', 6.43, 4.18, 0.65, 0.18, 8, C.muted);
text(slide, '张伟 · 尾号 1024', 7.42, 4.16, 1.5, 0.2, 9.5, C.ink, true, 'right');
text(slide, '付款账户', 6.43, 4.51, 0.65, 0.18, 8, C.muted);
text(slide, '储蓄卡 · 1024', 7.42, 4.49, 1.5, 0.2, 9.5, C.ink, false, 'right');
text(slide, '金额', 6.43, 4.84, 0.65, 0.18, 8, C.muted);
text(slide, '¥ 300.00', 7.42, 4.8, 1.5, 0.25, 13, C.ink, true, 'right');
rounded(slide, 6.42, 5.2, 1.12, 0.3, C.white, 'D8C386', 0.03);
rounded(slide, 7.72, 5.2, 1.46, 0.3, C.amber, C.amber, 0.03);
text(slide, '取消', 6.42, 5.28, 1.12, 0.13, 8, C.muted, true, 'center');
text(slide, '确认转账', 7.72, 5.28, 1.46, 0.13, 8, C.white, true, 'center');

// 输入框
rounded(slide, 2.75, 6.46, 6.7, 0.55, 'F7F9FB', C.line, 0.05);
text(slide, '输入你想办理的银行业务…', 3.08, 6.62, 4.8, 0.2, 9.5, '8B98A4');
addIcon(slide, 'mic', 8.46, 6.62, 0.18, 0.18, C.muted);
rounded(slide, 8.82, 6.56, 0.44, 0.34, C.navy, C.navy, 0.04);
addIcon(slide, 'send', 8.95, 6.65, 0.18, 0.18, C.white);

// 右侧执行轨迹
slide.addShape(S.rect, { x: 9.86, y: 0.84, w: 3.28, h: 6.47, fill: { color: 'F7F9FB' }, line: { color: 'F7F9FB' } });
slide.addShape(S.line, { x: 9.86, y: 0.84, w: 0, h: 6.47, line: { color: C.line, width: 0.8 } });
text(slide, '执行轨迹', 10.18, 1.04, 1.0, 0.3, 14, C.ink, true);
rounded(slide, 11.92, 1.08, 0.74, 0.25, C.softAmber, C.softAmber, 0.03);
text(slide, '等待确认', 11.92, 1.145, 0.74, 0.12, 7.5, '8A6212', true, 'center');

const steps = [
  ['理解意图', '账单分析 + 转账', 'done'],
  ['查询数据', '本月 38 笔交易', 'done'],
  ['生成计划', '2 个任务节点', 'done'],
  ['权限判断', '转账为黄色操作', 'active'],
  ['执行业务', '等待用户确认', 'wait']
];
steps.forEach((item, index) => {
  const y = 1.75 + index * 0.72;
  const color = item[2] === 'done' ? C.green : item[2] === 'active' ? C.amber : 'AAB4BC';
  slide.addShape(S.ellipse, { x: 10.18, y, w: 0.27, h: 0.27, fill: { color }, line: { color } });
  if (item[2] === 'done') addIcon(slide, 'check', 10.245, y + 0.065, 0.14, 0.14, C.white);
  else text(slide, String(index + 1), 10.18, y + 0.07, 0.27, 0.11, 7, C.white, true, 'center');
  text(slide, item[0], 10.62, y - 0.03, 1.05, 0.22, 10, C.ink, true);
  text(slide, item[1], 10.62, y + 0.25, 1.8, 0.18, 8, C.muted);
  if (index < steps.length - 1) slide.addShape(S.line, { x: 10.315, y: y + 0.28, w: 0, h: 0.44, line: { color: 'C8D0D7', width: 1 } });
});

rounded(slide, 10.16, 5.55, 2.52, 1.1, C.white, C.line, 0.045);
text(slide, '本次安全判断', 10.4, 5.78, 1.3, 0.22, 9.5, C.ink, true);
text(slide, '当日累计：¥300 / ¥1,000', 10.4, 6.12, 1.8, 0.18, 8, C.muted);
slide.addShape(S.rect, { x: 10.4, y: 6.43, w: 1.86, h: 0.08, fill: { color: 'E8EDF1' }, line: { color: 'E8EDF1' } });
slide.addShape(S.rect, { x: 10.4, y: 6.43, w: 0.56, h: 0.08, fill: { color: C.amber }, line: { color: C.amber } });

pptx.writeFile({ fileName: '银行Agent前端工作台预览.pptx' });
