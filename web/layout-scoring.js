const decisionSection=[...document.querySelectorAll('.doc-section')].find(section=>section.textContent.includes('布局引擎如何做决定'));
if(decisionSection){
  const scoring=document.createElement('section');
  scoring.className='doc-section scoring-explainer';
  scoring.innerHTML='<small>MATCH SCORING / CURRENT IMPLEMENTATION</small><h2>当前模板匹配评分算法</h2><p>引擎对每个同尺寸模板，用动态规划枚举“语素 ↔ 槽位”组合，最大化所有配对分数之和。模板总分再叠加覆盖率奖励。</p><div class="score-grid"><article><b>+46 · EXACT</b><span>组件 type 命中槽位 preferred</span></article><article><b>+30 · FAMILY</b><span>组件族命中 accepts</span></article><article><b>+12 · FOOTPRINT</b><span>类型不同，但 S/M/L 占地相近</span></article><article><b>+16 · ROLE</b><span>role 命中槽位角色倾向</span></article><article><b>+12 · PRIMARY</b><span>PRIMARY 进入 prominence ≥ 1.2 的高显著槽</span></article><article><b>+ priority</b><span>round(priority ÷ 20 × prominence)</span></article></div><pre>TemplateScore = Σ PairScore − 18 × 未填必需槽 − priority ÷ 5 × 未匹配语素 + round(coverage × 25)</pre><p>覆盖率低于 50% 直接进入 FREE；未匹配语素先扫描 12 列网格留白，无法放置且覆盖率低于 75% 时也进入 FREE。</p><div class="diversity-note"><b>近优多样性：避免运动类卡片总挤在同一版式</b><span>先取“与最高分相差不超过 18 分、且覆盖率相同”的候选带，再用 title + semanticKey 形成稳定语义签名，在候选带内做确定性散列选择。18 分来自 2×1 运动样本的候选分差校准，约为典型总分的 12%。不同运动主题可分散到不同近优模板；同一输入仍永远得到同一结果。明显更差的模板不会参与。</span></div>';
  decisionSection.after(scoring);
}
