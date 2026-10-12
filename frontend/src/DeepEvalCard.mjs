import React from 'react';

const h=React.createElement;

export function DeepEvalCard({evaluation,onRetry,busy=false}){
  const status=evaluation?.status||'pending';
  const unavailable=status==='unavailable';
  const loading=busy||status==='pending';
  const score=typeof evaluation?.score==='number'&&Number.isFinite(evaluation.score)
    ?`${Math.round(evaluation.score*100)}%`
    :'—';
  return h('section',{className:'panel qualityEvaluation', 'aria-labelledby':'quality-evaluation-title'},
    h('div',{className:'qualityHeader'},
      h('div',null,
        h('p',{className:'kicker'},'AI QUALITY EVALUATION'),
        h('h2',{id:'quality-evaluation-title'},'Property Recommendation Quality')
      ),
      h('span',{className:`qualityStatus ${unavailable?'unavailable':loading?'pending':'complete'}`},unavailable?'Evaluation unavailable':loading?'Running':'Complete')
    ),
    h('div',{className:'qualityResult'},
      h('div',{className:'qualityScore'},
        h('small',null,'GEval score'),
        h('strong',{'aria-label':`Property Recommendation Quality score ${score}`},score)
      ),
      h('div',{className:'qualityVerdict'},
        h('small',null,'Verdict'),
        h('strong',null,unavailable?'Evaluation unavailable':loading?'Evaluation running':evaluation?.verdict||'Evaluation unavailable')
      )
    ),
    h('div',{className:'qualityReason'},
      h('small',null,'Evaluation reason'),
      h('p',{role:unavailable?'status':undefined},loading?'DeepEval is evaluating the recommendation…':evaluation?.reason||'Evaluation unavailable')
    ),
    onRetry&&h('button',{className:'qualityRetry',onClick:onRetry,disabled:loading},loading?'Evaluating…':'Run evaluation again')
  );
}
