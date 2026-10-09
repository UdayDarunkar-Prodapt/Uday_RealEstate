from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import PropertyInput, FeedbackIn, WhatIfIn
from .database import initialize, save_valuation, save_feedback, save_evaluation
from .pipeline import ValuationService
from .evaluation.llm_judge import LLMJudge
from .config import OPENROUTER_API_KEY, PRIMARY_LLM_MODEL, FALLBACK_LLM_MODEL

app=FastAPI(title='Ames Valuation Assistant',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173'],allow_methods=['*'],allow_headers=['*'])
service=ValuationService(); persistence_ok=initialize(); judge=LLMJudge()
@app.get('/api/health')
def health(): return {'status':'ok','persistence_available':persistence_ok,**service.status()}
@app.get('/api/config/status')
def config_status(): return {'external_llm_configured':judge.configured(),'primary_llm_model':PRIMARY_LLM_MODEL or None,'fallback_llm_model':FALLBACK_LLM_MODEL or None,**service.status()}
@app.get('/api/model-info')
def model_info(): return {'features':__import__('backend.app.config',fromlist=['FEATURES']).FEATURES,**service.status()}
@app.post('/api/valuate')
def valuate(item:PropertyInput):
    result=service.valuate(item)
    if result['status']=='success':
        result['evaluation']=judge.evaluate(result)
        result['query_id']=save_valuation(item.query,result) if persistence_ok else None
        if persistence_ok: save_evaluation(result['query_id'],result['evaluation'])
    return result
@app.post('/api/search')
def search(item:PropertyInput):
    result=service.valuate(item)
    return {'status':result['status'],'property_features':result.get('property_features',{}),'comparables':result.get('comparables',[]),'retrieval':result.get('retrieval',{}),'message':result.get('message')}
@app.post('/api/compare')
def compare(item:PropertyInput): return search(item)
@app.post('/api/what-if')
def what_if(item:WhatIfIn):
    original=service.valuate(item.property)
    if original['status']!='success': return original
    changed=item.property.model_copy(update=item.changes); revised=service.valuate(changed)
    return {'status':'success','original_prediction':original['predicted_value'],'new_prediction':revised['predicted_value'],'difference':round(revised['predicted_value']-original['predicted_value'],2),'changed_features':item.changes,'note':'Model-based scenario estimate; it is not a causal effect.'}
@app.post('/api/feedback')
def feedback(item:FeedbackIn):
    if not persistence_ok or not save_feedback(item): raise HTTPException(503,'SQLite persistence unavailable; valuation remains available.')
    return {'status':'saved'}
@app.post('/api/evaluate')
def evaluate(item:PropertyInput):
    result=service.valuate(item)
    if result['status']!='success': return {'status':result['status'],'evaluation':None,'message':result.get('message')}
    evaluation=judge.evaluate(result)
    return {'status':'success','evaluation':evaluation,'note':'LLM-as-Judge evaluates explanation quality only; it never modifies the numeric valuation.'}
