from fastapi.testclient import TestClient

from backend.app.evaluation import deepeval_quality


VALUATION={
    'status':'success',
    'predicted_value':210000,
    'valuation_range':{'lower':190000,'upper':230000},
    'confidence':0.82,
    'risk_level':'LOW',
    'explanation':'Estimate grounded in similar historical sales.',
    'comparables':[{'SalePrice':205000}],
    'evidence':['3 bedroom property sold for $205,000'],
}


def test_deepeval_runs_the_existing_geval_metric(monkeypatch):
    captured={}

    class FakeBaseLLM:
        pass

    class FakeCaseParams:
        INPUT='input'
        ACTUAL_OUTPUT='actual_output'
        RETRIEVAL_CONTEXT='retrieval_context'

    class FakeTestCase:
        def __init__(self,**kwargs): captured['case']=kwargs

    class FakeGEval:
        def __init__(self,**kwargs): captured['metric']=kwargs
        def measure(self,case): captured['measured_case']=case
        score=0.84
        reason='Grounded in comparable sales and includes uncertainty.'

    monkeypatch.setattr(deepeval_quality,'ANTHROPIC_API_KEY','test-key')
    monkeypatch.setattr(deepeval_quality,'PRIMARY_LLM_MODEL','claude-sonnet-4-6')
    monkeypatch.setenv('DEEPEVAL_MODEL','claude-sonnet-4-6')
    monkeypatch.setattr(deepeval_quality,'_deepeval_types',lambda:(FakeBaseLLM,FakeGEval,FakeTestCase,FakeCaseParams))

    output=deepeval_quality.evaluate_recommendation_quality('3 bedroom home in Ames',VALUATION)

    assert output=={
        'status':'success',
        'metric_name':'Property Recommendation Quality',
        'score':0.84,
        'verdict':'Meets quality threshold',
        'reason':'Grounded in comparable sales and includes uncertainty.',
    }
    assert captured['metric']['name']=='Property Recommendation Quality'
    assert captured['metric']['threshold']==0.6
    assert len(captured['metric']['evaluation_params'])==3
    assert captured['case']['input']=='3 bedroom home in Ames'
    assert captured['case']['retrieval_context']==VALUATION['evidence']


def test_deepeval_failure_returns_unavailable_without_raising(monkeypatch):
    class FakeBaseLLM:
        pass

    class FakeCaseParams:
        INPUT='input'
        ACTUAL_OUTPUT='actual_output'
        RETRIEVAL_CONTEXT='retrieval_context'

    class FakeTestCase:
        def __init__(self,**kwargs): pass

    class FailingGEval:
        def __init__(self,**kwargs): pass
        def measure(self,case): raise TimeoutError('upstream timeout')

    monkeypatch.setattr(deepeval_quality,'ANTHROPIC_API_KEY','test-key')
    monkeypatch.setattr(deepeval_quality,'PRIMARY_LLM_MODEL','claude-sonnet-4-6')
    monkeypatch.setattr(deepeval_quality,'_deepeval_types',lambda:(FakeBaseLLM,FailingGEval,FakeTestCase,FakeCaseParams))
    output=deepeval_quality.evaluate_recommendation_quality('3 bedroom home',VALUATION)
    assert output['status']=='unavailable'
    assert output['verdict']=='Evaluation unavailable'
    assert output['score'] is None
    assert 'TimeoutError' in output['reason']


def test_deepeval_endpoint_returns_score_verdict_and_reason(monkeypatch):
    from backend.app import main
    monkeypatch.setattr(main,'checked_valuate',lambda item:dict(VALUATION))
    expected={'status':'success','metric_name':'Property Recommendation Quality','score':0.84,'verdict':'Meets quality threshold','reason':'Grounded in comparable sales.'}
    monkeypatch.setattr(main,'evaluate_recommendation_quality',lambda query,valuation:expected)
    response=TestClient(main.app).post('/api/deepeval/evaluate',json={'query':'3 bedroom home in Ames'})
    assert response.status_code==200
    assert response.json()=={'status':'success','evaluation':expected}


def test_valuate_keeps_working_and_marks_deepeval_pending(monkeypatch):
    from backend.app import main
    monkeypatch.setattr(main,'checked_valuate',lambda item:dict(VALUATION))
    monkeypatch.setattr(main.judge,'evaluate',lambda result:{'judge_method':'deterministic_judge_fallback'})
    monkeypatch.setattr(main,'persistence_ok',False)
    response=TestClient(main.app).post('/api/valuate',json={'query':'3 bedroom home in Ames'})
    assert response.status_code==200
    result=response.json()
    assert result['status']=='success'
    assert result['deepeval_evaluation']['status']=='pending'
