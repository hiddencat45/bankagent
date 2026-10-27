// Rebuild the evidence deck; no dependency is installed or upgraded by this script.
// ARTIFACT_MODULE points to @oai/artifact-tool/dist/artifact_tool.mjs.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const {Presentation, PresentationFile} = await import(pathToFileURL(process.env.ARTIFACT_MODULE).href);
const p = Presentation.create({slideSize:{width:1280,height:720}});
const build = path.join(root,'.desktop-tmp','deck-build');
await fs.mkdir(build,{recursive:true});
function text(s, value, x,y,w,h,size=28,color='#243e36',bold=false){
  const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  sh.text=value; sh.text.style={typeface:'Microsoft YaHei',fontSize:size,color,bold}; return sh;
}
function slide(title, note){
  const s=p.slides.add();s.background.fill='#f4f6f5';
  text(s,title,64,48,1152,90,42,'#164f42',true);
  text(s,`有度 · 2026-10-27 分支验收 · ${p.slides.items.length}`,64,672,1152,26,16,'#63766e');
  s.speakerNotes.text=note;return s;
}
function lines(s, rows){ rows.forEach((r,i)=>text(s,r,68,170+i*104,1140,88,29)); }
let s=slide('有度：可核对结果的银行 AI 模拟应用','本材料替换34页历史规划。基于c325aeb及交付核对分支。所有能力以docs/交付核对.md为准。未合并PR，不是生产银行。');
text(s,'普通表单与自然语言\n共用确认、业务服务和账本',68,180,1100,160,48,'#164f42',true);
text(s,'PySide6 独立窗口 · SQLite 本地账本 · 模型提出工具调用',68,390,1100,70,29);
text(s,'理财推荐尚未实现；界面仅两页预览；无独立安装包。\n本轮没有把测试通过等同于全部交付。',68,510,1100,100,28,'#9a3024');
s=slide('模型提出操作，服务端决定是否执行','src/bankagent/agent/query_loop.py、agent_graph.py、banking/bank_backend.py、storage.py、api/server.py。');
lines(s,['对话：查询实际数据，准备候选，再等用户确认。','表单：结构化字段直接进入同一准备与确认服务。','服务端：校验归属、金额、风险、授权与幂等，再提交账务。','结果：页面和助手读取同一账本，失败不写成成功。']);
s=slide('本轮真实模型的结果与失败都保留','docs/evidence/delivery-model-20261027.json。真实供应商，ASGI TestClient，隔离SQLite。七组达到各自断言，理财组未实现。不外推成功率，不是窗口验收。');
lines(s,['账单四轮追问、客户创建和发卡激活均得到实际回执。','卡未激活及冻结时拒付；解冻后支付12元成功。','双边37.50元转账、46改29再取消、41.50元批量均核对。','理财请求返回不支持，没有产品目录、画像或筛选结果。']);
s=slide('账户概览已经连接真实数据','docs/evidence/window-20261027/record.json。实际Windows窗口，1280×736逻辑像素，125%缩放。离线规则；窗口由脚本驱动，不是用户手测。');
s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,'docs/evidence/window-20261027/overview.png'))),contentType:'image/png',alt:'真实账户概览窗口',fit:'contain',position:{left:64,top:145,width:910,height:510}});
text(s,'实际余额\n实际卡片\n实际流水\n\n右侧助手共享\n当前身份',990,210,230,360,27);
s=slide('确认后的30元付款可以复查','docs/evidence/window-20261027/transfer-result.png及record.json。填40、返回修改30、确认、查余额。资金变化500000到497000分。');
s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,'docs/evidence/window-20261027/transfer-result.png'))),contentType:'image/png',alt:'转账后实际结果与助手查询',fit:'contain',position:{left:64,top:145,width:910,height:510}});
text(s,'填40元\n返回改30元\n重新确认\n\n5000元\n变为4970元',990,210,230,360,27);
s=slide('批量整批提交，重开核对业务记录','tests/test_batch_transfer.py、tests/test_funds_chain.py、tests/test_customer_onboarding.py。模型批量张伟18+李娜23.50=41.50元，余额495850分，重建服务公开接口读回。');
lines(s,['一次确认列全对象、各笔金额和总额。','同一事务复用单笔规则；任一项失败，整批不扣款。','网络未知只核对原决定；没有反向转账“假回滚”。','重启保留流水和批量回执，不恢复聊天或待确认任务。']);
s=slide('这些目标仍没有完整交付','docs/交付核对.md。理财仍属本次范围。生产实名非本次承诺；独立认证客户端未接。账号/卡号解析与新客户联系人入口缺失。');
lines(s,['理财推荐：画像、虚构产品目录、筛选与解释均未实现。','对象体验：账号/卡号、同名选择、新客户联系人维护有缺口。','高风险：服务端有门禁，桌面尚无独立认证通道。','桌面：预览待认可，其余页及EXE分发尚未完成。']);
s=slide('陌生人可以按文档复演一条完整链','docs/复演指南.md。此处为手工复演预期，不冒称已经由陌生人验收。请用新演示账本，已有账本按差额核对。');
lines(s,['Windows + Python 3.10，setup-desktop后打开start-desktop。','增开旅程账户得1000元，申请并激活旅程卡，消费12元。','转给张伟37.50元：旅程账户950.50元，张伟437.50元。','关闭重开查双方流水；再用模型修改、取消与查批量回执。']);
s=slide('现实价值与评估参考有明确边界','参考： https://github.com/langchain-ai/langgraph ; https://github.com/fastapi/fastapi ; https://github.com/meituan-longcat/vitabench ; https://openid.net/specs/fapi-security-profile-2_0-final.html 。2026-10-27核对。未运行VitaBench官方数据或评分器，未声称官方成绩。');
lines(s,['价值：验证自然语言办理与普通页面如何共享可信业务结果。','真实接入还需银行授权API、身份/强认证、对账与运维评审。','LangGraph、FastAPI是实际依赖；银行规则由本项目负责。','VitaBench启发多轮意图与最终状态评估；本项目没有官方成绩。']);
for(let i=0;i<p.slides.items.length;i++){
  const image=await p.export({slide:p.slides.items[i],format:'png',scale:1});
  await fs.writeFile(path.join(build,`slide-${i+1}.png`),new Uint8Array(await image.arrayBuffer()));
}
await (await PresentationFile.exportPptx(p)).save(path.join(build,'candidate.pptx'));
console.log('Rendered and exported',p.slides.items.length,'slides');
