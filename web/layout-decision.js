const baseRenderPreview=renderPreview;
renderPreview=function(spec){
  baseRenderPreview(spec);
  const box=document.getElementById('layoutDecision');
  const mode=spec.layoutMode||'FREE';
  const diagnostics=spec.diagnostics||{};
  const coverage=Math.round((diagnostics.confidence||0)*100);
  box.className='layout-decision '+(mode==='FREE'?'free':'matched');
  const title=box.querySelector('b'),detail=box.querySelector('span');
  if(mode==='FREE'){
    title.textContent='未命中合适模板 · 已进入自由模式 FREE';
    detail.textContent=(diagnostics.rationale||['模板覆盖率不足，使用确定性自由网格。']).join(' ');
  }else{
    title.textContent=`命中模板 · ${spec.template} · ${spec.templateName}`;
    const extended=mode==='TEMPLATE_EXTENDED'?' · 使用模板留白补位':'';
    detail.textContent=`来源 ${diagnostics.source||'模板库'} · 得分 ${diagnostics.score??'—'} · 覆盖率 ${coverage}% · ${mode}${extended}`;
  }
};
document.getElementById('form').addEventListener('submit',()=>{
  const box=document.getElementById('layoutDecision');
  box.className='layout-decision pending';
  box.querySelector('b').textContent='正在进行布局匹配…';
  box.querySelector('span').textContent='将根据尺寸、组件类型、role、priority 和占地体量评估候选模板。';
},{capture:true});
