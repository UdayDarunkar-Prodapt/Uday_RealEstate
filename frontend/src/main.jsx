import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';
import {DeepEvalCard} from './DeepEvalCard.mjs';

const API='http://localhost:8000/api';
const PROPERTY_PHOTOS=[
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=900&q=85',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=900&q=85',
  'https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=900&q=85',
  'https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=900&q=85',
  'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=900&q=85',
];
const SECTIONS=[
  {id:'model-evaluation',label:'Model evaluation',icon:'M',group:'Evaluation'},
  {id:'overview',label:'Overview',icon:'◫',group:'Workspace'},
  {id:'valuation',label:'Property valuation',icon:'⌂',group:'Workspace'},
  {id:'comparables',label:'Related properties',icon:'▦',group:'Analysis'},
  {id:'impacts',label:'Feature impacts',icon:'⌁',group:'Analysis'},
  {id:'evidence',label:'Evidence',icon:'▤',group:'Analysis'},
  {id:'safeguards',label:'Safeguards',icon:'◇',group:'Analysis'},
  {id:'explanation',label:'Explanation review',icon:'☷',group:'Evaluation'},
  {id:'quality',label:'AI quality evaluation',icon:'✳',group:'Evaluation'},
  {id:'feedback',label:'Feedback',icon:'↗',group:'Evaluation'},
];
const money=value=>value==null?'—':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(value);
const percentage=value=>value==null?'—':`${Math.round(value*100)}%`;
const display=value=>value==null?'—':String(value).replaceAll('_',' ');
const isValidSection=value=>SECTIONS.some(section=>section.id===value);

function SectionTitle({kicker,title,description}){
  return <div className="dashboardPageTitle"><p className="kicker">{kicker}</p><h1>{title}</h1>{description&&<p>{description}</p>}</div>;
}

function EmptyState({title='No valuation yet',children,onNavigate}){
  return <div className="emptyState"><span>⌂</span><h2>{title}</h2><p>{children||'Start with a property description to populate this section with its analysis.'}</p>{onNavigate&&<button onClick={onNavigate}>Describe a property <b>→</b></button>}</div>;
}

function EstimateCards({result}){
  return <>
    <div className="estimateHero"><div><span>ESTIMATED PROPERTY VALUE</span><strong>{money(result.predicted_value)}</strong><small>{result.explanation}</small></div><div className={`estimateRisk ${result.risk_level}`}><span>RISK LEVEL</span><b>{result.risk_level}</b></div></div>
    <div className="estimateCards">
      <article><small>ESTIMATED RANGE</small><strong>{money(result.valuation_range?.lower)} <i>to</i> {money(result.valuation_range?.upper)}</strong><p>Calculated uncertainty range</p></article>
      <article><small>CONFIDENCE</small><strong>{percentage(result.confidence)}</strong><div className="meter"><i style={{width:percentage(result.confidence)}}/></div><p>Evidence quality score</p></article>
      <article><small>VALUATION METHOD</small><strong className="estimateMethod">{display(result.valuation_method)}</strong><p>{display(result.retrieval?.retrieval_mode)}</p></article>
    </div>
  </>;
}

function RelatedProperties({comparables}){
  if(!comparables?.length)return <EmptyState title="No comparable properties">No comparable records were returned for this valuation.</EmptyState>;
  return <div className="dashboardPropertyGrid">
    {comparables.map((property,index)=><article className="propertyCard" key={property.property_id}>
      <div className="propertyPhoto"><img src={PROPERTY_PHOTOS[index%PROPERTY_PHOTOS.length]} alt={`Illustrative exterior for comparable ${index+1}; not an actual listing photo`}/><span>COMPARABLE 0{index+1}</span></div>
      <div className="propertyCardBody">
        <div className="propertyPrice"><strong>{money(property.SalePrice)}</strong><span>{property.similarity_score}% match</span></div>
        <p className="propertyLocation">{property.Neighborhood||'Ames'} · Built {property.YearBuilt||'—'}</p>
        <div className="propertyFacts"><span><b>{property.BedroomAbvGr??'—'}</b> beds</span><span><b>{property.FullBath??'—'}</b> baths</span><span><b>{property.GrLivArea?.toLocaleString()||'—'}</b> sq ft</span><span><b>{property.OverallQual??'—'}</b> quality</span></div>
        <p className="photoNote">Illustrative image; actual property photos are not available.</p>
      </div>
    </article>)}
  </div>;
}

function ImpactList({impacts}){
  if(!impacts?.length)return <p className="dashboardMuted">Feature impact information is not available for this valuation.</p>;
  return <div className="impactList">{impacts.map((impact,index)=><article className="impactRow" key={`${impact.feature}-${impact.neighborhood||index}`}>
    <div className="impactName">{impact.feature==='Neighborhood'?`Location: ${impact.neighborhood}`:display(impact.feature)}{impact.method==='historical_neighborhood_median'&&<small>Historical median difference · {impact.sample_count} sales · descriptive, not causal</small>}</div>
    <div className="impactTrack"><i className={impact.direction} style={{width:`${Math.min(100,Math.max(4,Math.abs(impact.impact)/500))}%`}}/></div>
    <strong>{impact.impact>=0?'+':''}{money(impact.impact)}</strong>
  </article>)}</div>;
}

function App(){
  const [query,setQuery]=useState('3 bedroom, 2 bathroom home in NAmes with 1800 sq ft, built 2005, quality 7');
  const [result,setResult]=useState(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  const [count,setCount]=useState(null);
  const [feedback,setFeedback]=useState('');
  const [valuationQuery,setValuationQuery]=useState('');
  const [modelEvaluation,setModelEvaluation]=useState(null);
  const [modelEvaluationLoading,setModelEvaluationLoading]=useState(false);
  const [modelEvaluationError,setModelEvaluationError]=useState('');
  const [activeSection,setActiveSection]=useState(()=>{const section=window.location.hash.slice(1);return isValidSection(section)?section:'overview'});
  const valuationSequence=useRef(0);
  const evaluationSequence=useRef(0);

  useEffect(()=>{fetch(`${API}/health`).then(response=>response.json()).then(data=>setCount(data.property_count)).catch(()=>{})},[]);
  useEffect(()=>{const restore=()=>{const section=window.location.hash.slice(1);setActiveSection(isValidSection(section)?section:'overview')};window.addEventListener('popstate',restore);return()=>window.removeEventListener('popstate',restore)},[]);
  useEffect(()=>{
    if(activeSection!=='model-evaluation'||modelEvaluation)return;
    let cancelled=false;
    setModelEvaluationLoading(true);setModelEvaluationError('');
    fetch(`${API}/model-evaluation`).then(async response=>{
      const data=await response.json();
      if(!response.ok)throw Error(data.detail||'Unable to load model evaluation metrics.');
      if(!cancelled)setModelEvaluation(data);
    }).catch(exception=>{if(!cancelled)setModelEvaluationError(exception.message||'Unable to load model evaluation metrics.');})
      .finally(()=>{if(!cancelled)setModelEvaluationLoading(false);});
    return()=>{cancelled=true;};
  },[activeSection,modelEvaluation]);

  const navigate=section=>{
    setActiveSection(section);
    window.history.pushState(null,'',`#${section}`);
    window.scrollTo({top:0,behavior:'smooth'});
  };

  const runDeepEval=async(description=valuationQuery,valuationId=valuationSequence.current)=>{
    const evaluationId=++evaluationSequence.current;
    const pending={status:'pending',metric_name:'Property Recommendation Quality',score:null,verdict:'Evaluation pending',reason:'DeepEval is evaluating the recommendation.'};
    setResult(current=>current&&valuationId===valuationSequence.current?{...current,deepeval_evaluation:pending}:current);
    try{
      const response=await fetch(`${API}/deepeval/evaluate`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:description})});
      const data=await response.json();
      if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'DeepEval request failed.');
      const evaluation=data.evaluation||{status:'unavailable',verdict:'Evaluation unavailable',score:null,reason:'DeepEval returned no evaluation.'};
      setResult(current=>current&&valuationId===valuationSequence.current&&evaluationId===evaluationSequence.current?{...current,deepeval_evaluation:evaluation}:current);
    }catch(exception){
      const evaluation={status:'unavailable',metric_name:'Property Recommendation Quality',score:null,verdict:'Evaluation unavailable',reason:exception.message||'DeepEval request failed.'};
      setResult(current=>current&&valuationId===valuationSequence.current&&evaluationId===evaluationSequence.current?{...current,deepeval_evaluation:evaluation}:current);
    }
  };

  const run=async()=>{
    const sequence=++valuationSequence.current;
    setLoading(true);setError('');setFeedback('');setResult(null);
    try{
      const response=await fetch(`${API}/valuate`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query})});
      const data=await response.json();
      if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Unable to value this property.');
      if(sequence!==valuationSequence.current)return;
      const pending={status:'pending',metric_name:'Property Recommendation Quality',score:null,verdict:'Evaluation pending',reason:'DeepEval is starting.'};
      setValuationQuery(query);setResult({...data,deepeval_evaluation:pending});
      void runDeepEval(query,sequence);
    }catch(exception){if(sequence===valuationSequence.current)setError(exception.message||'Unable to value this property.');}
    finally{if(sequence===valuationSequence.current)setLoading(false);}
  };

  const sendFeedback=async rating=>{
    try{
      const response=await fetch(`${API}/feedback`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query_id:result?.query_id,rating})});
      if(!response.ok)throw Error('Feedback could not be saved.');
      setFeedback('Thanks. Your rating will help prioritize evidence after enough feedback is collected.');
    }catch(exception){setFeedback(exception.message);}
  };

  const current=SECTIONS.find(section=>section.id===activeSection)||SECTIONS[0];
  const comparables=result?.comparables||[];
  const riskFactors=result?.risk_factors||[];
  const evidence=result?.evidence||[];

  return <div className="dashboardShell">
    <aside className="dashboardSidebar">
      <a className="dashboardBrand" href="#overview" onClick={event=>{event.preventDefault();navigate('overview')}}><span>H</span><b>HAVENS</b></a>
      <div className="sidebarCaption">PROPERTY INTELLIGENCE</div>
      {['Workspace','Analysis','Evaluation'].map(group=><div className="navGroup" key={group}>
        <p>{group}</p>
        {SECTIONS.filter(section=>section.group===group).map(section=><button key={section.id} className={activeSection===section.id?'active':''} onClick={()=>navigate(section.id)} aria-current={activeSection===section.id?'page':undefined}><span>{section.icon}</span>{section.label}{section.id==='quality'&&result?.deepeval_evaluation?.status==='pending'&&<i className="navPending"/>}</button>)}
      </div>)}
      <div className="sidebarFoot"><strong>{count?.toLocaleString()||'—'}</strong><span>historical properties<br/>in the Ames dataset</span></div>
    </aside>

    <main className="dashboardMain">
      <header className="dashboardTopbar"><div><span className="breadcrumb">HAVENS /</span> {current.label}</div><span className="localBadge"><i/> LOCAL VALUATION WORKSPACE</span></header>

      {activeSection==='overview'&&<section className="dashboardView">
        <SectionTitle kicker="DASHBOARD" title="Ames property intelligence" description="Run a valuation and explore each part of its evidence in a dedicated workspace."/>
        <div className="overviewHero"><div><p className="kicker">YOUR VALUATION WORKSPACE</p><h2>Property decisions,<br/><i>grounded in local evidence.</i></h2><p>Describe a home to estimate its value, compare historical properties, and inspect model quality.</p><button onClick={()=>navigate('valuation')}>Start a property valuation <b>→</b></button></div><div className="overviewHome"><img src={PROPERTY_PHOTOS[0]} alt="Illustrative home exterior"/><span>AMES · HISTORICAL SALES</span></div></div>
        <div className="overviewStats"><article><small>HISTORICAL RECORDS</small><strong>{count?.toLocaleString()||'—'}</strong><span>properties available for comparison</span></article><article><small>RELATED PROPERTIES</small><strong>{result?.status==='success'?comparables.length:'—'}</strong><span>{result?'from the latest valuation':'available after a valuation'}</span></article><article><small>LAST ESTIMATE</small><strong>{result?.status==='success'?money(result.predicted_value):'—'}</strong><span>{result?'saved in this workspace':'run a valuation to get started'}</span></article></div>
        <div className="overviewLinks"><div className="sectionTitleRow"><div><p className="kicker">ANALYSIS SECTIONS</p><h2>Explore the valuation</h2></div></div><div className="overviewLinkGrid">{SECTIONS.filter(section=>['comparables','impacts','evidence','safeguards','explanation','model-evaluation','quality'].includes(section.id)).map(section=><button key={section.id} onClick={()=>navigate(section.id)}><span>{section.icon}</span><strong>{section.label}</strong><i>Open section →</i></button>)}</div></div>
      </section>}

      {activeSection==='valuation'&&<section className="dashboardView">
        <SectionTitle kicker="VALUATION" title="Describe a property" description="Enter details about a home to estimate its value using the trained model and comparable Ames sales."/>
        <div className="valuationFormPanel"><label htmlFor="property-description">PROPERTY DESCRIPTION</label><textarea id="property-description" value={query} onChange={event=>setQuery(event.target.value)} placeholder="For example: 3 bedroom, 2 bathroom home in North Ames, 1,800 sq ft, built 2005, quality 7."/><div className="formActions"><span>Include bedrooms, bathrooms, living area, year built, quality, or neighborhood.</span><button onClick={run} disabled={loading}>{loading?'Analysing…':'Estimate property value'} <b>→</b></button></div>{error&&<p className="error" role="alert">{error}</p>}</div>
        {result?.status==='success'&&<div className="valuationSectionResult"><SectionTitle kicker="LATEST RESULT" title="Estimated property value" description="The summary and its supporting evidence are available in separate dashboard sections."/><EstimateCards result={result}/><div className="resultShortcuts"><button onClick={()=>navigate('comparables')}>View related properties</button><button onClick={()=>navigate('quality')}>Open AI quality evaluation</button></div></div>}
        {result?.status==='setup_required'&&<div className="dashboardNotice"><strong>Historical data is not ready yet.</strong><p>{result.message}</p></div>}
        {!result&&!loading&&<div className="valuationTip"><b>What happens next?</b><span>Your estimate, range, confidence, comparables, feature impacts, safeguards, and evaluations each have their own section in this dashboard.</span></div>}
      </section>}

      {activeSection==='comparables'&&<section className="dashboardView"><SectionTitle kicker="COMPARABLE PROPERTIES" title="Related historical homes" description="Property records selected to support the latest estimate. Images are illustrative; the dataset contains no listing photos."/>{result?.status==='success'?<RelatedProperties comparables={comparables}/>:<EmptyState onNavigate={()=>navigate('valuation')}>Run a valuation first to see its related historical properties.</EmptyState>}</section>}

      {activeSection==='impacts'&&<section className="dashboardView"><SectionTitle kicker="MODEL EXPLANATION" title="Feature impacts" description="Factors surfaced by the valuation model and historical neighborhood context."/>{result?.status==='success'?<div className="dashboardPanel"><ImpactList impacts={result.feature_impacts}/></div>:<EmptyState onNavigate={()=>navigate('valuation')}>Run a valuation first to see which features influenced the estimate.</EmptyState>}</section>}

      {activeSection==='evidence'&&<section className="dashboardView"><SectionTitle kicker="RETRIEVAL EVIDENCE" title="Evidence used" description="Retrieved property records and the search strategy behind the latest estimate."/>{result?.status==='success'?<div className="dashboardPanel"><div className="evidenceMeta"><span><small>RETRIEVAL METHOD</small><b>{display(result.retrieval?.retrieval_mode)}</b></span><span><small>LEXICAL SEARCH</small><b>{display(result.retrieval?.lexical_method)}</b></span><span><small>SEMANTIC STORE</small><b>{display(result.retrieval?.semantic_store)}</b></span></div><ol className="evidenceList">{evidence.map((item,index)=><li key={index}><span>0{index+1}</span><p>{item}</p></li>)}</ol></div>:<EmptyState onNavigate={()=>navigate('valuation')}>Run a valuation first to inspect the retrieved evidence.</EmptyState>}</section>}

      {activeSection==='safeguards'&&<section className="dashboardView"><SectionTitle kicker="LIMITS & FALLBACKS" title="Safeguards" description="Review input completeness, retrieval relaxation, model fallbacks, and uncertainty for this estimate."/>{result?.status==='success'?<div className="dashboardPanel safeguardPanel"><div className={`safeguardStatus ${result.risk_level}`}><span>RISK SIGNAL</span><strong>{result.risk_level}</strong><small>{result.fallback_used?'Fallback or retrieval relaxation was used.':'Normal valuation path.'}</small></div><div className="safeguardDetails"><h2>Checks and limitations</h2><ul>{riskFactors.length?riskFactors.map((factor,index)=><li key={index}>{factor}</li>):<li>Comparable evidence and input completeness were checked.</li>}<li>{result.retrieval?.fallback_used?result.retrieval.fallback_reason:'No retrieval relaxation was required.'}</li><li>This is an estimate, not a guarantee or causal claim.</li></ul></div></div>:<EmptyState onNavigate={()=>navigate('valuation')}>Safeguard details appear after a valuation has completed.</EmptyState>}</section>}

      {activeSection==='explanation'&&<section className="dashboardView"><SectionTitle kicker="LLM-AS-JUDGE" title="Explanation review" description="The language model checks whether the written explanation is grounded in retrieved facts. It never changes the estimate."/>{result?.status==='success'?<div className="dashboardPanel explanationPanel"><div className="evaluationSummary"><strong>{result.evaluation?.judge_method==='llm_as_judge'?'Reviewed by Claude':'Local validation active'}</strong><span>{result.evaluation?.judge_model||'Deterministic fallback'}</span></div><div className="reviewedExplanation"><h3>Explanation reviewed</h3><p>{result.explanation}</p></div><div className="judgeScores"><label>Groundedness <b>{percentage(result.evaluation?.groundedness)}</b></label><label>Relevance <b>{percentage(result.evaluation?.relevance)}</b></label><label>Completeness <b>{percentage(result.evaluation?.completeness)}</b></label></div><p className="explanationVerdict">{result.evaluation?.verdict||'No explanation evaluation was returned.'}</p></div>:<EmptyState onNavigate={()=>navigate('valuation')}>Run a valuation first to review its explanation.</EmptyState>}</section>}

      {activeSection==='model-evaluation'&&<section className="dashboardView"><SectionTitle kicker="HELD-OUT MODEL METRICS" title="Valuation model evaluation" description="These error metrics describe how the trained valuation model performed on its training holdout data. They are separate from DeepEval's recommendation quality score."/>{modelEvaluationLoading&&<div className="dashboardNotice" role="status">Loading saved model metrics...</div>}{modelEvaluationError&&<p className="error" role="alert">{modelEvaluationError}</p>}{!modelEvaluationLoading&&modelEvaluation?.status==='success'&&<><div className="modelMetricGrid">{[['MAE','mae','Average absolute prediction error, in dollars. Lower means predictions were closer on average.'],['RMSE','rmse','Root mean squared error, in dollars. It gives larger prediction misses extra weight. Lower is better.'],['MSE','mse','Mean squared error, in dollars squared. Squaring errors makes large misses count much more. Lower is better.']].map(([label,key,description])=><article className="modelMetricCard" key={key}><span>{label}</span><strong>{modelEvaluation.metrics?.[key]==null?'Unavailable':key==='mse'?`${Number(modelEvaluation.metrics[key]).toLocaleString('en-US',{maximumFractionDigits:2})} USD^2`:Number(modelEvaluation.metrics[key]).toLocaleString('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2})}</strong><p>{description}</p></article>)}</div><div className="dashboardPanel modelEvaluationNote"><strong>{display(modelEvaluation.model_name)} - holdout evaluation</strong><p>{modelEvaluation.sample_description} These are model validation errors, not a guarantee of the error for an individual property.</p>{modelEvaluation.mse_reconstructed&&<p>MSE is reconstructed from the saved RMSE because this model bundle predates direct MSE storage. Retrain the model to save exact MSE.</p>}</div></>}{!modelEvaluationLoading&&modelEvaluation?.status==='unavailable'&&<EmptyState title="Model metrics unavailable">{modelEvaluation.message||'Train the valuation model to create evaluation metrics.'}</EmptyState>}</section>}

      {activeSection==='quality'&&<section className="dashboardView"><SectionTitle kicker="DEEPEVAL · GEVAL" title="AI quality evaluation" description="The existing Property Recommendation Quality metric evaluates the completed recommendation against its input and retrieved evidence."/>{result?.status==='success'?<DeepEvalCard evaluation={result.deepeval_evaluation} onRetry={()=>runDeepEval(valuationQuery,valuationSequence.current)}/>:<EmptyState onNavigate={()=>navigate('valuation')}>Run a valuation first, then evaluate the recommendation quality.</EmptyState>}</section>}

      {activeSection==='feedback'&&<section className="dashboardView"><SectionTitle kicker="RANKING FEEDBACK" title="Improve future comparisons" description="Feedback can make a small adjustment to comparable ranking after enough ratings have been collected."/>{result?.status==='success'?<div className="dashboardPanel feedbackPanel"><h2>Was this evidence useful?</h2><p>Your rating helps prioritize comparable records. It never changes the valuation or property price.</p><div><button onClick={()=>sendFeedback(1)}>Helpful</button><button onClick={()=>sendFeedback(-1)}>Not helpful</button></div>{feedback&&<p className="feedbackStatus" role="status">{feedback}</p>}</div>:<EmptyState onNavigate={()=>navigate('valuation')}>Complete a valuation first to rate its evidence.</EmptyState>}</section>}
    </main>
  </div>;
}

createRoot(document.getElementById('root')).render(<App/>);
