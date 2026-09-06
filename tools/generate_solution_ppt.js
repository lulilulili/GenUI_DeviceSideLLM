const pptxgen = require('C:/Users/huzimo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pptxgenjs');
const path = require('path');
const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'GenUI LAB';
pptx.subject = '端侧小模型驱动的确定性 GenUI 技术方案';
pptx.title = 'GenUI 端侧生成式界面技术方案';
pptx.company = 'GenUI LAB';
pptx.lang = 'zh-CN';
pptx.theme = {headFontFace:'Microsoft YaHei', bodyFontFace:'Microsoft YaHei', lang:'zh-CN'};
pptx.defineSlideMaster({title:'MASTER',background:{color:'07111D'},objects:[
  {rect:{x:0,y:0,w:13.333,h:.08,fill:{color:'2674ED'},line:{color:'2674ED'}}},
  {text:{text:'GenUI LAB  ·  DEVICE-SIDE GENERATIVE UI',options:{x:.55,y:.18,w:5.8,h:.25,fontFace:'Aptos',fontSize:9,color:'7E9AB7',charSpacing:1.1,margin:0}}},
  {text:{text:'技术方案 / v0.3',options:{x:11.55,y:.18,w:1.2,h:.25,fontSize:9,color:'7E9AB7',align:'right',margin:0}}},
  {line:{x:.55,y:7.14,w:12.2,h:0,line:{color:'203247',width:1}}},
  {text:{text:'模型决定表达什么 · 代码决定放在哪里 · 协议决定如何渲染',options:{x:.55,y:7.21,w:8,h:.18,fontSize:8,color:'607A96',margin:0}}}
],slideNumber:{x:12.35,y:7.18,w:.35,h:.2,color:'607A96',fontSize:8,align:'right'}});

const C={bg:'07111D',panel:'0D1A29',panel2:'112338',line:'263B52',text:'E9F2FC',muted:'91A8BF',blue:'2674ED',cyan:'5DE0C0',purple:'9A70E8',orange:'EF9D48',red:'E66A78',white:'FFFFFF'};
const addTitle=(s,kicker,title,sub='')=>{s.addText(kicker.toUpperCase(),{x:.6,y:.56,w:4.8,h:.2,fontSize:9,bold:true,color:C.blue,charSpacing:1.4,margin:0});s.addText(title,{x:.6,y:.82,w:12.1,h:.58,fontSize:26,bold:true,color:C.text,margin:0,breakLine:false});if(sub)s.addText(sub,{x:.62,y:1.47,w:11.8,h:.42,fontSize:11.5,color:C.muted,margin:0,breakLine:false});};
const card=(s,x,y,w,h,title,body,accent=C.blue)=>{s.addShape(pptx.ShapeType.roundRect,{x,y,w,h,rectRadius:.08,fill:{color:C.panel},line:{color:C.line,width:1}});s.addShape(pptx.ShapeType.rect,{x,y,w:.06,h,fill:{color:accent},line:{color:accent}});s.addText(title,{x:x+.22,y:y+.18,w:w-.4,h:.28,fontSize:14,bold:true,color:C.text,margin:0});s.addText(body,{x:x+.22,y:y+.58,w:w-.42,h:h-.72,fontSize:10.5,color:C.muted,breakLine:false,margin:0,bullet:body.includes('\n•')?{type:'bullet'}:undefined});};
const pill=(s,x,y,w,text,color=C.blue)=>{s.addShape(pptx.ShapeType.roundRect,{x,y,w,h:.34,rectRadius:.12,fill:{color,transparency:78},line:{color,transparency:20}});s.addText(text,{x:x+.08,y:y+.08,w:w-.16,h:.15,fontSize:8.5,bold:true,color,align:'center',margin:0});};
const arrow=(s,x,y,w=.35)=>s.addShape(pptx.ShapeType.chevron,{x,y,w,h:.34,fill:{color:'466683'},line:{color:'466683'}});
const flowNode=(s,x,y,w,num,title,kind='code')=>{const color=kind==='model'?C.purple:kind==='future'?C.orange:C.blue;s.addShape(pptx.ShapeType.roundRect,{x,y,w,h:1.02,rectRadius:.06,fill:{color:C.panel2},line:{color}});s.addText(num,{x:x+.15,y:y+.13,w:.35,h:.18,fontSize:8,bold:true,color,margin:0});s.addText(title,{x:x+.15,y:y+.45,w:w-.3,h:.25,fontSize:11,bold:true,color:C.text,align:'center',margin:0});};

// 1
{
 const s=pptx.addSlide('MASTER');
 s.addText('GENUI',{x:.7,y:1.18,w:4,h:.7,fontSize:47,bold:true,color:C.text,margin:0,charSpacing:-1});
 s.addText('端侧小模型驱动的\n确定性生成式界面技术方案',{x:.7,y:2.02,w:8.7,h:1.55,fontSize:32,bold:true,color:C.text,breakLine:false,margin:0});
 s.addText('Morpheme 语义协议 × 模板/自由布局引擎 × DSL / A2UI / HTML 多协议渲染',{x:.75,y:3.86,w:9.8,h:.55,fontSize:14,color:C.muted,margin:0});
 ['端侧 3B','确定性后处理','PDF 设计范式','多协议输出'].forEach((t,i)=>pill(s,.75+i*1.65,4.7,1.42,t,[C.purple,C.cyan,C.orange,C.blue][i]));
 s.addShape(pptx.ShapeType.arc,{x:9.9,y:1.25,w:2.3,h:2.3,adjustPoint:.35,rotate:25,line:{color:C.blue,width:12,transparency:10},fill:{color:C.bg,transparency:100}});
 s.addShape(pptx.ShapeType.arc,{x:10.35,y:1.7,w:1.4,h:1.4,adjustPoint:.35,rotate:205,line:{color:C.cyan,width:8},fill:{color:C.bg,transparency:100}});
 s.addText('2026.09',{x:.75,y:6.45,w:2,h:.25,fontSize:10,color:'6D86A1',margin:0});
}

// 2
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Executive summary','核心判断：让小模型只做它擅长的语义选择','把随机性限制在最小边界，布局、数据和代码全部转入可测试的确定性系统。');
 card(s,.65,2.15,3.75,2.25,'01 · Morpheme','端侧模型输出精简语义语素：组件类型、角色、标签、语义键和数据类型。\n\n不生成坐标、CSS、真实 API 或模板 ID。',C.purple);
 card(s,4.78,2.15,3.75,2.25,'02 · Layout Engine','按尺寸筛选 PDF 模板族，以 role、priority、组件族和占地进行全局匹配；无法适配时进入受约束自由布局。',C.cyan);
 card(s,8.91,2.15,3.75,2.25,'03 · Render Adapter','统一 RenderSpec 同时映射为 GenUI DSL、A2UI v0.9 NDJSON、HTML + CSS，渲染体系可以独立替换。',C.blue);
 s.addText('设计原则',{x:.7,y:4.92,w:1.1,h:.25,fontSize:11,bold:true,color:C.orange,margin:0});
 s.addText('小模型负责“表达什么”  →  确定性代码负责“是否合法、放在哪里”  →  协议适配器负责“如何交付”',{x:.7,y:5.35,w:11.9,h:.48,fontSize:17,bold:true,color:C.text,align:'center',margin:0});
}

// 3
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Problem framing','为什么不能让 3B 直接生成完整 UI','自由生成会同时承担语义理解、布局、代码和设计系统，错误难定位且难复用。');
 const cols=[['语义漂移','状态被写成进度、数量被写成百分比、瞬时动作被写成开关。'],['布局不稳定','同一提示词可能产生不同 DOM 和坐标，无法保证品牌、一致性与可访问性。'],['Token / 延迟','完整代码输出长，CPU decode 成为主要瓶颈；纠错会进一步放大成本。'],['协议锁定','直接生成 HTML 会把意图、布局和前端技术栈耦合在一起。']];
 cols.forEach((v,i)=>card(s,.65+(i%2)*6.05,2.0+Math.floor(i/2)*2.05,5.65,1.65,v[0],v[1],[C.red,C.orange,C.purple,C.blue][i]));
 s.addText('解法：缩小模型责任边界，并建立可观测、可回归的中间协议。',{x:.7,y:6.2,w:11.7,h:.35,fontSize:16,bold:true,color:C.cyan,align:'center',margin:0});
}

// 4
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Architecture','端到端总体架构','模型调用仅发生在 MorphemeDraft 生成；语义审校作为默认关闭的实验支路。');
 const names=[['01','User Prompt','code'],['02','Prompt / Schema','code'],['03','3B Morpheme','model'],['04','Validate / Reconcile','code'],['05','Info Budget','code'],['06','Mock / API Data','future'],['07','Layout Engine','code'],['08','RenderSpec','code'],['09','DSL · A2UI · H5','code']];
 names.forEach((n,i)=>{const row=i<5?0:1,idx=i<5?i:i-5,w=row?2.45:2.18,x=.55+idx*(row?3.05:2.5),y=row?4.35:2.25;flowNode(s,x,y,w,n[0],n[1],n[2]);if((row===0&&i<4)||(row===1&&i<8))arrow(s,x+w+.12,y+.34,.3)});
 s.addShape(pptx.ShapeType.downArrow,{x:11.55,y:3.48,w:.45,h:.58,fill:{color:'466683'},line:{color:'466683'}});
 pill(s,9.55,1.75,2.35,'可选：第二次 LLM 审校',C.orange);
}

// 5
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Model boundary','MorphemeDraft：模型唯一输出','短字段降低 decode 成本；Schema 控制枚举、数量和卡片尺寸。');
 s.addShape(pptx.ShapeType.roundRect,{x:.7,y:2.0,w:5.05,h:4.25,fill:{color:'050C14'},line:{color:C.line},rectRadius:.06});
 s.addText('{\n  "s":"CARD", "z":"2x2",\n  "d":"AUTO", "t":"上海天气",\n  "m":[\n    {"k":"STATUS","r":"SECONDARY",\n     "l":"天气","q":"weather.condition","f":"ENUM"},\n    {"k":"METRIC","r":"PRIMARY",\n     "l":"气温","q":"weather.temperature","f":"NUMBER"},\n    {"k":"PROGRESS","r":"SECONDARY",\n     "l":"湿度","q":"weather.humidity","f":"PERCENTAGE"}\n  ]\n}',{x:.95,y:2.3,w:4.55,h:3.65,fontFace:'Consolas',fontSize:11,color:'CDE2F5',margin:0,breakLine:false});
 const fields=[['s','Surface','CARD / PAGE'],['z','Size','AUTO / 2×1 / 2×2 / 3×2 / 3×3'],['d','Density','AUTO / COMPACT / COMFORTABLE / DETAILED'],['m[]','Morpheme','k · r · l · q · f']];
 fields.forEach((f,i)=>{s.addShape(pptx.ShapeType.roundRect,{x:6.35,y:2.05+i*.93,w:5.85,h:.68,fill:{color:C.panel2},line:{color:i===3?C.purple:C.blue}});s.addText(f[0],{x:6.55,y:2.25+i*.93,w:.7,h:.2,fontSize:12,bold:true,color:i===3?C.purple:C.blue,margin:0});s.addText(f[1],{x:7.3,y:2.23+i*.93,w:1.1,h:.2,fontSize:11,bold:true,color:C.text,margin:0});s.addText(f[2],{x:8.45,y:2.23+i*.93,w:3.45,h:.2,fontSize:9.5,color:C.muted,margin:0});});
}

// 6
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Semantic safety','模型之后：通用语义一致性约束','Schema 合法不等于语义正确；确定性层处理高置信、跨领域的组件—数据关系。');
 const rules=[['数量 / 人数 / 容量','METRIC + NUMBER'],['状态 / 在线 / 离线','STATUS + ENUM'],['比例 / 进度','PROGRESS + PERCENTAGE'],['瞬时动作','BUTTON + UNKNOWN'],['持久开关','SWITCH + BOOLEAN'],['多条同类实体','LIST + LIST']];
 rules.forEach((r,i)=>{const x=.7+(i%2)*6.0,y=2.02+Math.floor(i/2)*1.25;s.addShape(pptx.ShapeType.roundRect,{x,y,w:5.55,h:.88,fill:{color:C.panel},line:{color:C.line}});s.addText(r[0],{x:x+.2,y:y+.29,w:2.35,h:.2,fontSize:11,color:C.muted,margin:0});s.addText('→  '+r[1],{x:x+2.55,y:y+.27,w:2.7,h:.22,fontSize:12,bold:true,color:i%2?C.cyan:C.blue,margin:0});});
 s.addText('失败处理',{x:.72,y:6.0,w:1,h:.2,fontSize:10,bold:true,color:C.orange,margin:0});
 s.addText('JSON 解码失败 → 最多一次定向纠错；类型冲突 → 确定性校正并记录 corrections；空间不足 → 降级或裁剪低优先级语素。',{x:1.75,y:5.93,w:10.3,h:.42,fontSize:11,color:C.text,margin:0});
}

// 7
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Card budget','卡片尺寸同时约束信息丰度与视觉空间','尺寸不是模型自由发挥的描述，而是 Schema 数量上限、组件成本预算和渲染比例的共同输入。');
 const sizes=[['2×1','3','420×210','核心状态 + 轻量指标'],['2×2','8','360×360','核心信息 + 辅助状态 + 少量操作'],['3×2','11','540×360','横向服务、快捷入口、媒体和图表'],['3×3','14','480×480','完整数据、列表和多个操作']];
 sizes.forEach((r,i)=>{const x=.68+i*3.08;s.addShape(pptx.ShapeType.roundRect,{x,y:2.1,w:2.72,h:3.35,fill:{color:C.panel},line:{color:i===0?C.cyan:C.line}});s.addText(r[0],{x:x+.2,y:2.35,w:2.3,h:.5,fontSize:26,bold:true,color:C.text,align:'center',margin:0});pill(s,x+.66,3.08,1.4,'预算 '+r[1],C.blue);s.addText(r[2],{x:x+.2,y:3.68,w:2.3,h:.28,fontSize:13,bold:true,color:C.cyan,align:'center',margin:0});s.addText(r[3],{x:x+.3,y:4.25,w:2.1,h:.65,fontSize:10.5,color:C.muted,align:'center',valign:'mid',margin:0});});
 s.addText('组件成本示例：TEXT / METRIC / STATUS / BUTTON = 1；PROGRESS / SLIDER = 2；LIST = 4',{x:.7,y:5.95,w:11.9,h:.35,fontSize:12,color:C.orange,align:'center',margin:0});
}

// 8
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Template layout','模板模式：依从设计范式，而不是硬编码业务','模板描述槽位空间和倾向；相近组件族或占地可替换，最终由全局评分决定。');
 const steps=[['尺寸过滤','只保留 2×1 / 2×2 / 3×2 / 3×3 同尺寸模板'],['全局评分','Exact 类型 > 同组件族 > 相近 footprint；叠加 role / priority'],['槽位分配','最大化必要语素覆盖、首要信息显著度和操作可达性'],['留白补位','剩余完整空间可放入未匹配内容，标记 TEMPLATE_EXTENDED']];
 steps.forEach((v,i)=>{flowNode(s,.7+i*3.08,2.15,2.62,'0'+(i+1),v[0]);s.addText(v[1],{x:.83+i*3.08,y:3.35,w:2.35,h:.85,fontSize:9.5,color:C.muted,align:'center',margin:0});if(i<3)arrow(s,3.42+i*3.08,2.49,.27)});
 s.addShape(pptx.ShapeType.roundRect,{x:1.35,y:4.72,w:10.5,h:1.25,fill:{color:C.panel2},line:{color:C.cyan}});
 s.addText('Template score = 覆盖率 + 类型/组件族适配 + role 显著度 + priority + 空间利用 − 溢出与碎片惩罚',{x:1.65,y:5.15,w:9.9,h:.35,fontSize:14,bold:true,color:C.text,align:'center',margin:0});
}

// 9
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Free layout','自由模式：不是“随便放”，而是受约束的布局求解','当模板覆盖率过低或重要组件无槽位时，进入可重复、可验证的自由布局通路。');
 const stages=[['A','语义排序','WARNING / PRIMARY / ACTION / SECONDARY'],['B','空间估算','依据组件 footprint、文本长度和最小触控面积'],['C','区域分组','标题、主信息、详情、动作、媒体形成视觉组'],['D','网格装箱','12 列网格，Best-Fit / Skyline 候选求解'],['E','视觉校正','对齐、平衡、留白、孤岛、狭缝与溢出评分']];
 stages.forEach((v,i)=>{const y=1.95+i*.9;s.addShape(pptx.ShapeType.roundRect,{x:.75,y,w:5.3,h:.64,fill:{color:C.panel},line:{color:i===4?C.cyan:C.line}});s.addText(v[0],{x:.92,y:y+.2,w:.3,h:.18,fontSize:9,bold:true,color:C.blue,margin:0});s.addText(v[1],{x:1.35,y:y+.17,w:1.3,h:.22,fontSize:11,bold:true,color:C.text,margin:0});s.addText(v[2],{x:2.7,y:y+.16,w:3.1,h:.28,fontSize:9.2,color:C.muted,margin:0});});
 s.addShape(pptx.ShapeType.roundRect,{x:6.7,y:1.95,w:5.25,h:4.25,fill:{color:'091522'},line:{color:C.line}});
 for(let i=1;i<12;i++)s.addShape(pptx.ShapeType.line,{x:6.7+i*5.25/12,y:1.95,w:0,h:4.25,line:{color:'1D3348',width:.5}});
 for(let i=1;i<12;i++)s.addShape(pptx.ShapeType.line,{x:6.7,y:1.95+i*4.25/12,w:5.25,h:0,line:{color:'1D3348',width:.5}});
 [['PRIMARY',6.83,2.1,3.0,1.75,C.blue],['STATUS',9.98,2.1,1.82,1.05,C.cyan],['DETAILS',9.98,3.3,1.82,1.5,C.purple],['ACTIONS',6.83,4.05,3.0,1.0,C.orange]].forEach(v=>{s.addShape(pptx.ShapeType.roundRect,{x:v[1],y:v[2],w:v[3],h:v[4],fill:{color:v[5],transparency:72},line:{color:v[5]}});s.addText(v[0],{x:v[1],y:v[2]+v[4]/2-.1,w:v[3],h:.2,fontSize:9,bold:true,color:C.text,align:'center',margin:0});});
}

// 10
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Design evidence','PDF 设计范式是模板库与回归集的共同来源','每页首行抽象为空间模板，下面实例转写为确定性 Morpheme，用于验证匹配与渲染。');
 const imgs=['pdf-2x1.jpg','pdf-2x2.jpg','pdf-3x2.jpg','pdf-3x3.jpg'];
 imgs.forEach((f,i)=>{const x=.65+(i%2)*6.08,y=1.95+Math.floor(i/2)*2.3;s.addImage({path:path.join(__dirname,'..','web','assets',f),x,y,w:5.65,h:1.82,sizing:'contain'});pill(s,x+.1,y+.1,.72,['2×1','2×2','3×2','3×3'][i],C.blue)});
 s.addText('当前：PDF 实例已集成到布局页面，可查看 Prompt、确定性 Morpheme、LayoutPlan、多协议代码和实际渲染。',{x:.72,y:6.58,w:11.8,h:.28,fontSize:10.5,color:C.muted,align:'center',margin:0});
}

// 11
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Render contract','RenderSpec：布局与渲染协议之间的稳定契约','协议适配器只消费统一的槽位矩形、组件内容和设计 Token，前端体系替换不反向影响模型。');
 flowNode(s,.7,2.45,2.35,'01','MorphemeSpec');arrow(s,3.2,2.78,.35);flowNode(s,3.7,2.45,2.35,'02','LayoutPlan');arrow(s,6.2,2.78,.35);flowNode(s,6.7,2.45,2.35,'03','RenderSpec');
 ['GenUI DSL','A2UI v0.9','HTML + CSS'].forEach((t,i)=>{s.addShape(pptx.ShapeType.roundRect,{x:10.1,y:1.75+i*1.25,w:2.35,h:.72,fill:{color:C.panel2},line:{color:[C.cyan,C.purple,C.blue][i]}});s.addText(t,{x:10.25,y:2.0+i*1.25,w:2.05,h:.2,fontSize:11,bold:true,color:C.text,align:'center',margin:0});});
 s.addShape(pptx.ShapeType.chevron,{x:9.38,y:2.77,w:.42,h:.38,fill:{color:'466683'},line:{color:'466683'}});
 s.addText('未来可增加 Flutter / Compose / ArkUI / 新版 A2UI，仅新增 Renderer Adapter。',{x:.8,y:5.35,w:11.5,h:.45,fontSize:15,bold:true,color:C.cyan,align:'center',margin:0});
}

// 12
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Protocol adapters','同源多协议输出','一次生成同时产生三种协议，运行页可直接切换、检查和复制。');
 card(s,.65,2.0,3.72,3.7,'GenUI DSL','紧凑 brace-tuple JSONL\n对接 _askr mini-parser\n适合底层 GenUI 图结构\n\n{"@generated-card", "catalog", {...}}',C.cyan);
 card(s,4.8,2.0,3.72,3.7,'A2UI v0.9','NDJSON 消息流\ncreateSurface + updateComponents\n每条更新只包含一个组件\n\n{"version":"v0.9", "createSurface":{...}}',C.purple);
 card(s,8.95,2.0,3.72,3.7,'HTML + CSS','可独立运行的 H5 产物\ncard.html + card.css + variables\n适合演示、调试和未来 Web 交付\n\n<article class="genui-card">',C.blue);
}

// 13
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Observability','工作台：把黑盒生成变成可定位的流水线','每个里程碑统一记录 input、output、elapsedMs、Token 和错误；预览与代码来自同一个 RenderSpec。');
 const steps=['输入预处理','Prompt / Schema','模型调用','JSON 校验','字段补齐','类型校正','信息预算','数据注入','模板匹配','RenderSpec','协议映射'];
 steps.forEach((t,i)=>{const x=.7+(i%4)*3.0,y=1.95+Math.floor(i/4)*1.22;s.addShape(pptx.ShapeType.roundRect,{x,y,w:2.65,h:.78,fill:{color:C.panel},line:{color:i===2?C.purple:C.line}});s.addShape(pptx.ShapeType.ellipse,{x:x+.18,y:y+.29,w:.16,h:.16,fill:{color:i===2?C.purple:C.cyan},line:{color:i===2?C.purple:C.cyan}});s.addText(String(i+1).padStart(2,'0')+' · '+t,{x:x+.45,y:y+.26,w:1.95,h:.2,fontSize:9.8,color:C.text,margin:0});});
 s.addText('统一事件',{x:.75,y:5.95,w:1,h:.2,fontSize:10,bold:true,color:C.blue,margin:0});
 s.addText('{ stage, status, input, output, elapsedMs, usage: { inputTokens, outputTokens, prefillMs, decodeMs } }',{x:1.8,y:5.87,w:10.5,h:.38,fontFace:'Consolas',fontSize:10.5,color:'CDE2F5',margin:0});
}

// 14
{
 const s=pptx.addSlide('MASTER');addTitle(s,'3B experiment','第二次 LLM 语义审校：保留实验开关，不默认启用','Qwen2.5 3B 在四类高风险用例上的审校没有形成稳定质量增益。');
 const rows=[['单次生成','15.9 s','387','89'],['开启审校','25.3 s','610','166'],['变化','+59%','+58%','+87%']];
 ['模式','平均耗时','Input Token','Output Token'].forEach((t,i)=>s.addText(t,{x:.85+i*2.85,y:2.05,w:2.5,h:.28,fontSize:11,bold:true,color:C.muted,align:i?'center':'left',margin:0}));
 rows.forEach((r,ri)=>r.forEach((v,i)=>{s.addShape(pptx.ShapeType.rect,{x:.72+i*2.85,y:2.48+ri*.72,w:2.72,h:.58,fill:{color:ri===2?'32251B':C.panel},line:{color:C.line}});s.addText(v,{x:.85+i*2.85,y:2.68+ri*.72,w:2.45,h:.2,fontSize:11,bold:ri===2,color:ri===2?C.orange:C.text,align:i?'center':'left',margin:0});}));
 card(s,.72,5.05,5.72,1.15,'有限收益','联系人用例中删除了可能臆造的操作。',C.cyan);
 card(s,6.86,5.05,5.72,1.15,'明显风险','误删“预订按钮”，并把“暂停按钮”改成开关。',C.red);
}

// 15
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Evaluation','当前验证状态与边界','通过不等于完成：现有数据多数参与过规则开发，需要冻结独立测试集。');
 card(s,.7,2.0,3.75,2.0,'27 项工程测试','覆盖 Morpheme 结构、通用类型校正、预算、模板匹配、槽位不重叠以及 DSL / A2UI / HTML 输出。',C.cyan);
 card(s,4.8,2.0,3.75,2.0,'PDF 回归集','68 条实例已转写为确定性 Morpheme，可逐条查看 Prompt、布局计划、代码和渲染结果。',C.orange);
 card(s,8.9,2.0,3.75,2.0,'RawIntent 历史评测','63 条用例均曾通过；最终一次全量为 62/63，修复后未再次执行完整全量，需严格区分口径。',C.purple);
 s.addText('下一步评测重点',{x:.7,y:4.7,w:1.5,h:.25,fontSize:11,bold:true,color:C.blue,margin:0});
 s.addText('独立未调优集 · 语义字段准确率 · 模板依从度 · 自由布局美观度 · 文本溢出 · P50/P95 · 冷/热启动',{x:.7,y:5.18,w:11.9,h:.45,fontSize:15,bold:true,color:C.text,align:'center',margin:0});
}

// 16
{
 const s=pptx.addSlide('MASTER');addTitle(s,'SFT strategy','SFT 主线：先建设黄金评测集，再训练','目标不是让模型学会前端代码，而是稳定输出正确、精简、不过度推断的 MorphemeDraft。');
 const loop=[['真实与边界场景',1.0,2.15],['黄金 Morpheme 标注',4.0,1.65],['3B 推理与错误分类',7.15,2.15],['Prompt / 规则基线',8.7,4.25],['困难样本与反例',5.55,5.1],['SFT + 冻结集回归',2.25,4.25]];
 loop.forEach((v,i)=>{s.addShape(pptx.ShapeType.roundRect,{x:v[1],y:v[2],w:2.35,h:.75,fill:{color:C.panel2},line:{color:i===5?C.purple:C.blue}});s.addText(v[0],{x:v[1]+.12,y:v[2]+.26,w:2.1,h:.2,fontSize:10.5,bold:true,color:C.text,align:'center',margin:0});});
 [[3.35,2.35,4.0,2.0],[6.4,2.6,7.2,2.35],[8.95,3.05,9.15,4.08],[8.0,5.15,7.9,5.15],[5.35,5.3,4.7,5.18],[2.45,4.1,1.95,3.05]].forEach(a=>s.addShape(pptx.ShapeType.chevron,{x:a[0],y:a[1],w:.35,h:.28,rotate:a[0]>8?90:0,fill:{color:'466683'},line:{color:'466683'}}));
 s.addText('关键样本：状态/进度、数量/比例、按钮/开关、单实体/列表、明确需求/模型臆造、各尺寸信息裁剪。',{x:.9,y:6.35,w:11.4,h:.3,fontSize:11,color:C.muted,align:'center',margin:0});
}

// 17
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Roadmap','建议实施路线','语义线与布局线通过稳定 MorphemeSpec 解耦，可以并行演进。');
 const phases=[['P0 · 当前','冻结 Morpheme v0.1\n完善独立评测集\n校准通用一致性规则'],['P1 · 模板准确性','建立模板质量指标\n逐条回归 PDF 实例\n处理文本与组件压力'],['P2 · 自由布局','实现受约束网格求解\n视觉评分与降级策略\n模板无法覆盖时兜底'],['P3 · 模型优化','积累困难样本\nSFT 3B Morpheme 输出\n与更强模型对照'],['P4 · 工程对接','接入真实数据/API\n接入 _askr DSL/A2UI Renderer\n扩展 Page / Form / Dialog']];
 phases.forEach((p,i)=>{const x=.55+i*2.52;s.addShape(pptx.ShapeType.roundRect,{x,y:2.0,w:2.22,h:3.85,fill:{color:C.panel},line:{color:i===0?C.cyan:C.line}});s.addText(p[0],{x:x+.16,y:2.28,w:1.9,h:.3,fontSize:12,bold:true,color:i===0?C.cyan:C.blue,align:'center',margin:0});s.addText(p[1],{x:x+.22,y:3.0,w:1.78,h:1.8,fontSize:10.5,color:C.muted,align:'center',breakLine:false,margin:0});if(i<4)arrow(s,x+2.28,3.7,.18)});
}

// 18
{
 const s=pptx.addSlide('MASTER');addTitle(s,'Conclusion','最终形态：可训练、可验证、可替换的 GenUI 工程','不是让模型生成一段“看起来像 UI”的代码，而是构建一条稳定的界面编译流水线。');
 const quote='自然语言  →  Morpheme  →  确定性校验  →  布局求解  →  RenderSpec  →  多协议渲染';
 s.addText(quote,{x:.8,y:2.0,w:11.7,h:.6,fontSize:19,bold:true,color:C.text,align:'center',margin:0});
 card(s,.85,3.05,3.6,1.65,'模型可训练','评测集、错误分类和 SFT 都围绕稳定 MorphemeDraft 展开。',C.purple);
 card(s,4.87,3.05,3.6,1.65,'布局可验证','模板依从与自由模式都以确定性评分、槽位约束和回归测试验收。',C.cyan);
 card(s,8.89,3.05,3.6,1.65,'渲染可替换','DSL、A2UI、HTML 共享 RenderSpec，未来协议升级不会重构模型链路。',C.blue);
 s.addText('下一阶段重点：黄金 Morpheme 数据集 + 模板布局质量体系 + 受约束自由布局算法',{x:.9,y:5.55,w:11.5,h:.48,fontSize:16,bold:true,color:C.orange,align:'center',margin:0});
}

pptx.writeFile({fileName:path.join(__dirname,'..','artifacts','GenUI端侧生成式界面技术方案.pptx')});
