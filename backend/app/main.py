from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import PropertyInput, FeedbackIn, WhatIfIn
from .database import initialize, save_valuation, save_feedback, save_evaluation
from .pipeline import ValuationService, InvalidPropertyFeatures
from .evaluation.llm_judge import LLMJudge
from .evaluation.deepeval_quality import evaluate_recommendation_quality, unavailable as deepeval_unavailable
from .config import PRIMARY_LLM_MODEL, FALLBACK_LLM_MODEL

app=FastAPI(title='Ames Valuation Assistant',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173'],allow_methods=['*'],allow_headers=['*'])
service=ValuationService(); persistence_ok=initialize(); judge=LLMJudge()
def checked_valuate(item):
    try: return service.valuate(item)
    except InvalidPropertyFeatures as exc: raise HTTPException(422,detail=str(exc)) from exc
@app.get('/api/health')
def health(): return {'status':'ok','persistence_available':persistence_ok,**service.status()}
@app.get('/api/config/status')
def config_status(): return {'external_llm_configured':judge.configured(),'llm_provider':'anthropic','primary_llm_model':PRIMARY_LLM_MODEL or None,'fallback_llm_model':FALLBACK_LLM_MODEL or None,**service.status()}
@app.get('/api/model-info')
def model_info(): return {'features':service.predictor.features,**service.status()}
@app.get('/api/model-evaluation')
def model_evaluation():
    metrics=service.predictor.evaluation_metrics()
    if metrics is None:
        return {'status':'unavailable','model_name':None,'evaluation_type':'holdout','metrics':None,'message':'Train the valuation model to create holdout evaluation metrics.'}
    return {'status':'success','model_name':service.predictor.bundle.get('model_name','valuation model'),'evaluation_type':'holdout','metrics':metrics,'sample_description':'Metrics are calculated on the 20% holdout split used during training (random_state=42).','explanations':{'mae':'Mean absolute error: the average absolute difference between predicted and actual sale prices, in dollars. Lower is better.','rmse':'Root mean squared error: the typical error scale in dollars, with larger misses penalized more heavily. Lower is better.','mse':'Mean squared error: the average squared difference in dollars squared, so large misses receive extra weight. Lower is better.'},'mse_reconstructed': 'mse' not in (service.predictor.bundle.get('metrics') or {})}
@app.post('/api/valuate')
def valuate(item:PropertyInput):
    result=checked_valuate(item)
    if result['status']=='success':
        result['evaluation']=judge.evaluate(result)
        result['deepeval_evaluation']={'status':'pending','metric_name':'Property Recommendation Quality','score':None,'verdict':'Evaluation pending','reason':'DeepEval will run separately so it cannot delay the valuation.'}
        result['query_id']=save_valuation(item.query,result) if persistence_ok else None
        if persistence_ok: save_evaluation(result['query_id'],result['evaluation'])
    return result
@app.post('/api/search')
def search(item:PropertyInput):
    result=checked_valuate(item)
    return {'status':result['status'],'property_features':result.get('property_features',{}),'comparables':result.get('comparables',[]),'retrieval':result.get('retrieval',{}),'message':result.get('message')}
@app.post('/api/compare')
def compare(item:PropertyInput): return search(item)
@app.post('/api/what-if')
def what_if(item:WhatIfIn):
    original=checked_valuate(item.property)
    if original['status']!='success': return original
    changed=item.property.model_copy(update=item.changes); revised=checked_valuate(changed)
    return {'status':'success','original_prediction':original['predicted_value'],'new_prediction':revised['predicted_value'],'difference':round(revised['predicted_value']-original['predicted_value'],2),'changed_features':item.changes,'note':'Model-based scenario estimate; it is not a causal effect.'}
@app.post('/api/feedback')
def feedback(item:FeedbackIn):
    if not persistence_ok or not save_feedback(item): raise HTTPException(503,'SQLite persistence unavailable; valuation remains available.')
    return {'status':'saved'}
@app.post('/api/evaluate')
def evaluate(item:PropertyInput):
    result=checked_valuate(item)
    if result['status']!='success': return {'status':result['status'],'evaluation':None,'message':result.get('message')}
    evaluation=judge.evaluate(result)
    return {'status':'success','evaluation':evaluation,'note':'LLM-as-Judge evaluates explanation quality only; it never modifies the numeric valuation.'}

@app.post('/api/deepeval/evaluate')
def evaluate_quality(item:PropertyInput):
    """Run the single GEval quality metric for this property's recommendation."""
    result=checked_valuate(item)
    if result['status']!='success':
        return {'status':'unavailable','evaluation':deepeval_unavailable('A completed property valuation is required before DeepEval can run.')}
    try:
        evaluation=evaluate_recommendation_quality(item.query,result)
    except Exception as exc:
        # Keep an optional external evaluation from affecting property valuation.
        evaluation=deepeval_unavailable(f'DeepEval could not complete this evaluation ({type(exc).__name__}).')
    return {'status':evaluation['status'],'evaluation':evaluation}
