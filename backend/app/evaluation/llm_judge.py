"""Grounded LLM-as-Judge for explanations; never changes numerical valuation outputs."""
import json
import time
from urllib import request, error
from ..config import ANTHROPIC_API_KEY, PRIMARY_LLM_MODEL, FALLBACK_LLM_MODEL, LLM_TIMEOUT_SECONDS

JUDGE_ENDPOINT = "https://api.anthropic.com/v1/messages"

class LLMJudge:
    def configured(self):
        return bool(ANTHROPIC_API_KEY and PRIMARY_LLM_MODEL)

    def evaluate(self, valuation: dict) -> dict:
        """Judge the evidence-grounded explanation, with primary/fallback LLM and deterministic degradation."""
        if not self.configured():
            return self._deterministic(valuation, "LLM judge is not configured.")
        errors=[]
        for model in filter(None, [PRIMARY_LLM_MODEL, FALLBACK_LLM_MODEL]):
            try:
                output = self._call(model, self._messages(valuation))
                return self._validate(output, model)
            except Exception as exc:
                errors.append(f"{model}: {type(exc).__name__}")
        return self._deterministic(valuation, "LLM judge unavailable after configured fallback: " + "; ".join(errors))

    def _call(self, model, messages):
        payload=json.dumps({"model":model,"max_tokens":700,"temperature":0,"system":messages[0]["content"],"messages":messages[1:]}).encode()
        last=None
        for attempt in range(2):
            req=request.Request(JUDGE_ENDPOINT,data=payload,headers={"x-api-key":ANTHROPIC_API_KEY,"anthropic-version":"2023-06-01","Content-Type":"application/json"},method="POST")
            try:
                with request.urlopen(req,timeout=LLM_TIMEOUT_SECONDS) as response:
                    data=json.loads(response.read().decode("utf-8"))
                    content="".join(block.get("text","") for block in data["content"] if block.get("type")=="text")
                    return self._parse_json(content)
            except (error.URLError, error.HTTPError, KeyError, json.JSONDecodeError) as exc:
                last=exc
                if attempt == 0: time.sleep(0.5)
        raise last

    @staticmethod
    def _parse_json(content):
        """Parse a JSON object even when Claude wraps it in a code fence or prose."""
        decoder=json.JSONDecoder()
        for index,char in enumerate(content):
            if char!="{": continue
            try:
                value,_=decoder.raw_decode(content[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(value,dict): return value
        raise ValueError("Claude response did not contain a valid JSON object")

    def _messages(self, valuation):
        evidence=valuation.get("evidence", [])
        facts={"property_features":valuation.get("property_features"),"predicted_value":valuation.get("predicted_value"),"valuation_range":valuation.get("valuation_range"),"confidence":valuation.get("confidence"),"risk_level":valuation.get("risk_level"),"retrieval":valuation.get("retrieval"),"risk_factors":valuation.get("risk_factors"),"feature_impacts":valuation.get("feature_impacts"),"evidence":evidence}
        return [
            {"role":"system","content":"You are a strict evaluator, not a valuation agent. Assess ONLY whether EXPLANATION is grounded in FACTS. Never calculate or revise property values. Return JSON only: {groundedness: number 0..1, relevance: number 0..1, completeness: number 0..1, evidence_usage: number 0..1, reasoning_quality: number 0..1, verdict: string, unsupported_claims: [string]}. If no unsupported claims exist use []."},
            {"role":"user","content":"FACTS:\n"+json.dumps(facts,ensure_ascii=False)+"\nEXPLANATION:\n"+str(valuation.get("explanation",""))}
        ]

    def _validate(self, output, model):
        fields=["groundedness","relevance","completeness","evidence_usage","reasoning_quality"]
        scores={name:float(output[name]) for name in fields}
        if any(score < 0 or score > 1 for score in scores.values()): raise ValueError("Judge score outside 0..1")
        claims=output.get("unsupported_claims",[])
        if not isinstance(claims,list) or not all(isinstance(v,str) for v in claims): raise ValueError("Invalid unsupported_claims")
        return {**{key:round(value,3) for key,value in scores.items()},"verdict":str(output.get("verdict",""))[:500],"unsupported_claims":claims[:10],"judge_method":"llm_as_judge","judge_model":model,"fallback_used":False}

    def _deterministic(self, valuation, reason):
        # These are calculated checks, not fabricated LLM scores.
        has_evidence=bool(valuation.get("evidence")); has_risk=bool(valuation.get("risk_factors") is not None); has_explanation=bool(valuation.get("explanation"))
        return {"groundedness":1.0 if has_evidence else 0.0,"relevance":1.0 if has_explanation else 0.0,"completeness":round((int(has_evidence)+int(has_risk)+int(has_explanation))/3,3),"evidence_usage":1.0 if has_evidence else 0.0,"reasoning_quality":None,"verdict":"Deterministic validation only; no LLM judgment was produced.","unsupported_claims":[],"judge_method":"deterministic_judge_fallback","judge_model":None,"fallback_used":True,"fallback_reason":reason}
