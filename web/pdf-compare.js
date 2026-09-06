const previewHost=document.querySelector('.inspect-preview');
if(previewHost){
  const generatedPreview=document.getElementById('casePreview');
  const comparison=document.createElement('div');
  comparison.className='compare-previews';
  const pdfFigure=document.createElement('figure');
  pdfFigure.innerHTML='<div class="pdf-case-frame"><img id="pdfCaseImage" alt="PDF 中的原始卡片实例"></div><figcaption>PDF 原始设计实例</figcaption>';
  const generatedFigure=document.createElement('figure');
  const generatedCaption=document.createElement('figcaption');
  generatedCaption.textContent='当前布局算法渲染';
  generatedFigure.append(generatedPreview,generatedCaption);
  comparison.append(pdfFigure,generatedFigure);
  previewHost.replaceChildren(comparison);
  const originalInspect=inspect;
  inspect=function(test,result){
    document.getElementById('pdfCaseImage').src=`/assets/pdf-cases/${test.id}.jpg`;
    originalInspect(test,result);
  };
}
