"""DeepEval GEval for the current property recommendation."""
import asyncio
import json
import logging
import os
from urllib import request

from ..config import ANTHROPIC_API_KEY, LLM_TIMEOUT_SECONDS, PRIMARY_LLM_MODEL

LOGGER=logging.getLogger(__name__)
METRIC_NAME='Property Recommendation Quality'
METRIC_CRITERIA=(
    'Judge whether the recommendation uses the supplied property description, '
    'reports a plausible estimate grounded in the provided historical comparable '
    'evidence, identifies uncertainty, and avoids unsupported or causal claims.'
)
METRIC_THRESHOLD=0.6
ANTHROPIC_MESSAGES_ENDPOINT='https://api.anthropic.com/v1/messages'


def unavailable(reason):
    return {
        'status':'unavailable',
        'metric_name':METRIC_NAME,
        'score':None,
        'verdict':'Evaluation unavailable',
        'reason':reason,
    }


def _deepeval_types():
    from deepeval.models import DeepEvalBaseLLM
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase
    try:
        from deepeval.test_case import SingleTurnParams as CaseParams
    except ImportError:
        from deepeval.test_case import LLMTestCaseParams as CaseParams
    return DeepEvalBaseLLM,GEval,LLMTestCase,CaseParams


def make_model_class(base_llm):
    """Build the Claude adapter using the same Messages API as the app judge."""
    class ClaudeDeepEvalModel(base_llm):
        def __init__(self,model): self.model=model
        def load_model(self): return self
        def get_model_name(self): return self.model
        def generate(self,prompt):
            payload=json.dumps({
                'model':self.model,
                'max_tokens':2048,
                'temperature':0,
                'messages':[{'role':'user','content':prompt}],
            }).encode()
            req=request.Request(
                ANTHROPIC_MESSAGES_ENDPOINT,
                data=payload,
                headers={
                    'x-api-key':ANTHROPIC_API_KEY,
                    'anthropic-version':'2023-06-01',
                    'Content-Type':'application/json',
                },
                method='POST',
            )
            with request.urlopen(req,timeout=LLM_TIMEOUT_SECONDS) as response:
                data=json.loads(response.read().decode('utf-8'))
            return ''.join(block.get('text','') for block in data['content'] if block.get('type')=='text')
        async def a_generate(self,prompt): return await asyncio.to_thread(self.generate,prompt)
    return ClaudeDeepEvalModel


def evaluate_recommendation_quality(query,valuation):
    """Run the existing single GEval metric against one completed valuation."""
    if not ANTHROPIC_API_KEY:
        return unavailable('Add ANTHROPIC_API_KEY to .env to run DeepEval with Claude.')
    try:
        DeepEvalBaseLLM,GEval,LLMTestCase,CaseParams=_deepeval_types()
        model_name=os.getenv('DEEPEVAL_MODEL') or PRIMARY_LLM_MODEL
        if not model_name:
            return unavailable('No Claude model is configured for DeepEval.')
        ClaudeDeepEvalModel=make_model_class(DeepEvalBaseLLM)
        actual={
            'predicted_value':valuation.get('predicted_value'),
            'valuation_range':valuation.get('valuation_range'),
            'confidence':valuation.get('confidence'),
            'risk_level':valuation.get('risk_level'),
            'explanation':valuation.get('explanation'),
            'comparables':valuation.get('comparables'),
        }
        test_case=LLMTestCase(
            input=query,
            actual_output=json.dumps(actual,ensure_ascii=False),
            retrieval_context=valuation.get('evidence') or [],
        )
        metric=GEval(
            name=METRIC_NAME,
            criteria=METRIC_CRITERIA,
            evaluation_params=[CaseParams.INPUT,CaseParams.ACTUAL_OUTPUT,CaseParams.RETRIEVAL_CONTEXT],
            model=ClaudeDeepEvalModel(model_name),
            threshold=METRIC_THRESHOLD,
        )
        metric.measure(test_case)
        score=float(metric.score)
        if not 0<=score<=1:
            raise ValueError('DeepEval returned a score outside 0..1')
        return {
            'status':'success',
            'metric_name':METRIC_NAME,
            'score':round(score,4),
            'verdict':'Meets quality threshold' if score>=METRIC_THRESHOLD else 'Below quality threshold',
            'reason':str(metric.reason or 'DeepEval did not provide a reason.')[:2000],
        }
    except Exception as exc:
        LOGGER.exception('DeepEval recommendation evaluation failed')
        return unavailable(f'DeepEval could not complete this evaluation ({type(exc).__name__}).')
