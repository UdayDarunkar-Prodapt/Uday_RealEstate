"""Run real DeepEval quality checks on live valuation recommendations."""
import asyncio
import json
import os
import sys
from pathlib import Path
from urllib import request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from deepeval.models import DeepEvalBaseLLM
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase
try:
    from deepeval.test_case import SingleTurnParams as CaseParams
except ImportError:
    from deepeval.test_case import LLMTestCaseParams as CaseParams
from backend.app.pipeline import ValuationService
from backend.app.schemas import PropertyInput
from backend.app.config import ANTHROPIC_API_KEY, PRIMARY_LLM_MODEL

API_KEY=ANTHROPIC_API_KEY
MODEL=os.getenv('DEEPEVAL_MODEL') or PRIMARY_LLM_MODEL
if not API_KEY or not MODEL:
    raise SystemExit('Set ANTHROPIC_API_KEY and optionally DEEPEVAL_MODEL in .env to run DeepEval with Claude.')

class ClaudeJudge(DeepEvalBaseLLM):
    def __init__(self,model): self.model=model
    def load_model(self): return self
    def get_model_name(self): return self.model
    def generate(self,prompt):
        payload=json.dumps({'model':self.model,'max_tokens':2048,'temperature':0,'messages':[{'role':'user','content':prompt}]}).encode()
        req=request.Request('https://api.anthropic.com/v1/messages',data=payload,headers={'x-api-key':API_KEY,'anthropic-version':'2023-06-01','Content-Type':'application/json'},method='POST')
        with request.urlopen(req,timeout=45) as response:
            data=json.loads(response.read().decode())
            return ''.join(block.get('text','') for block in data['content'] if block.get('type')=='text')
    async def a_generate(self,prompt): return await asyncio.to_thread(self.generate,prompt)

def main():
    service=ValuationService()
    scenarios=[
        '3 bedroom, 2 bathroom home in NAmes with 1800 sq ft, built 2005, quality 7',
        '4 bedroom, 3 bathroom home in CollgCr with 2400 sq ft, built 1998, quality 8',
    ]
    metric=GEval(name='Property recommendation quality',criteria='Judge whether the recommendation uses the supplied property description, reports a plausible estimate grounded in the provided historical comparable evidence, identifies uncertainty, and avoids unsupported or causal claims.',evaluation_params=[CaseParams.INPUT,CaseParams.ACTUAL_OUTPUT,CaseParams.RETRIEVAL_CONTEXT],model=ClaudeJudge(MODEL),threshold=.6)
    scores=[]
    for query in scenarios:
        result=service.valuate(PropertyInput(query=query))
        if result.get('status')!='success': raise SystemExit(f"Valuation unavailable for evaluation: {result.get('message')}")
        actual={'predicted_value':result['predicted_value'],'valuation_range':result['valuation_range'],'confidence':result['confidence'],'risk_level':result['risk_level'],'explanation':result['explanation'],'comparables':result['comparables']}
        case=LLMTestCase(input=query,actual_output=json.dumps(actual),retrieval_context=result['evidence'])
        metric.measure(case)
        scores.append({'input':query,'score':metric.score,'reason':metric.reason})
    print(json.dumps({'dataset_cases':len(scores),'metric':metric.name,'results':scores,'mean_score':sum(x['score'] for x in scores)/len(scores)},indent=2))

if __name__=='__main__': main()
