import json

from backend.app.evaluation import llm_judge


def test_claude_json_parser_accepts_markdown_fence():
    output=llm_judge.LLMJudge._parse_json('Result:\n```json\n{"groundedness": 1}\n```')
    assert output=={'groundedness':1}


def test_claude_messages_api_is_used_when_configured(monkeypatch):
    monkeypatch.setattr(llm_judge, 'ANTHROPIC_API_KEY', 'test-anthropic-key')
    monkeypatch.setattr(llm_judge, 'PRIMARY_LLM_MODEL', 'claude-sonnet-4-6')
    captured = {}
    expected = {
        'groundedness': 0.9,
        'relevance': 0.8,
        'completeness': 0.7,
        'evidence_usage': 0.9,
        'reasoning_quality': 0.8,
        'verdict': 'Grounded in comparable evidence.',
        'unsupported_claims': [],
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({'content': [{'type': 'text', 'text': json.dumps(expected)}]}).encode()

    def fake_urlopen(req, timeout):
        captured['url'] = req.full_url
        captured['headers'] = req.headers
        captured['payload'] = json.loads(req.data)
        captured['timeout'] = timeout
        return Response()

    monkeypatch.setattr(llm_judge.request, 'urlopen', fake_urlopen)
    judge = llm_judge.LLMJudge()
    assert judge.configured()
    result = judge.evaluate({'explanation': 'Evidence based.', 'evidence': ['Comparable home']})

    assert captured['url'] == 'https://api.anthropic.com/v1/messages'
    assert captured['headers']['X-api-key'] == 'test-anthropic-key'
    assert captured['headers']['Anthropic-version'] == '2023-06-01'
    assert captured['payload']['model'] == 'claude-sonnet-4-6'
    assert result['judge_method'] == 'llm_as_judge'
    assert result['judge_model'] == 'claude-sonnet-4-6'
