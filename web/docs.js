const nodeExamples={
  '用户输入':['生成上海天气卡片，突出气温','{"prompt":"生成上海天气卡片，突出气温","cardSize":"2x2"}'],
  'Prompt / Schema':['用户提示词 + cardSize=2x2','system: 只输出 MorphemeDraft\nschema: m.maxItems=6'],
  '端侧模型生成':['system + user + JSON Schema','{"s":"CARD","z":"2x2","t":"上海天气","m":[...]}'],
  'JSON 与协议校验':['模型原始 JSON 文本','{"valid":true,"errors":[]}'],
  'Morpheme 确定性补齐':['{"k":"METRIC","r":"PRIMARY","q":"weather.temperature","f":"NUMBER"}','{"id":"m1","type":"METRIC","priority":90,"content":{}}'],
  '类型一致性校正':['{"type":"STATUS","semanticKey":"contacts.count","valueType":"PERCENTAGE"}','{"type":"METRIC","valueType":"NUMBER","correction":"COUNT"}'],
  '信息预算':['size=2x1，3 个语素，cost=4','{"capacity":3,"used":3,"substitutions":["PROGRESS→METRIC"]}'],
  'Mock 数据适配':['{"semanticKey":"weather.temperature","valueType":"NUMBER"}','{"value":24,"unit":"°C","trend":"STABLE"}'],
  '布局规划':['2x2 + METRIC(PRIMARY) + STATUS(SECONDARY)','{"templateId":"2x2_metric_status","slots":[{"id":"main","rect":{"x":0,"y":0,"w":8,"h":7}}]}'],
  'RenderSpec':['MorphemeSpec + LayoutPlan','{"version":"0.2","grid":{"columns":12,"rows":12},"slots":[...]}'],
  '协议生成':['同一个 RenderSpec','DSL: {"@generated-card",...}\nA2UI: {"createSurface":...}\nHTML: <article class="genui-card">'],
  '界面渲染':['RenderSpec 或目标协议','2×2 卡片预览 + 可复制的三种协议代码']
};
document.querySelectorAll('.flow-card').forEach(card=>{
  card.title=card.dataset.desc;
  card.addEventListener('click',()=>{
    document.querySelectorAll('.flow-card.selected').forEach(node=>node.classList.remove('selected'));
    card.classList.add('selected');
    document.getElementById('nodeTitle').textContent=card.dataset.title;
    document.getElementById('nodeDesc').textContent=card.dataset.desc;
    document.getElementById('nodeInput').textContent=card.dataset.input;
    document.getElementById('nodeOutput').textContent=card.dataset.output;
    const examples=nodeExamples[card.dataset.title]||['—','—'];
    document.getElementById('nodeInputExample').textContent=examples[0];
    document.getElementById('nodeOutputExample').textContent=examples[1];
    document.getElementById('nodeInspector').scrollIntoView({behavior:'smooth',block:'nearest'});
  });
});
