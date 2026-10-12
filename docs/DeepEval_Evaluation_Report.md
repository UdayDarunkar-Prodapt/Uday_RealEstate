# DeepEval Evaluation Report

## Report status

This report describes the DeepEval evaluation configured in the project. **A live DeepEval run was not performed while preparing this report, so no score, verdict, or mean score is claimed.** The configured evaluator calls Claude through the Anthropic API and may incur provider usage charges. When run, the script prints the metric score and reason for each sample case and the mean score.

## Evaluation objective

Assess whether a property recommendation uses the supplied property description, is grounded in retrieved historical comparable-property evidence, communicates uncertainty, and avoids unsupported or causal claims. DeepEval evaluates recommendation quality only; it does not generate or change the predicted property value.

## Metric and configuration

| Item | Configuration |
|---|---|
| Framework | DeepEval |
| Metric | One GEval metric: `Property Recommendation Quality` |
| Criteria | Use the supplied property description; ground the estimate in historical comparable evidence; identify uncertainty; avoid unsupported or causal claims. |
| Evaluation inputs | `INPUT`, `ACTUAL_OUTPUT`, and `RETRIEVAL_CONTEXT` |
| Score scale | DeepEval GEval score in the 0–1 range |
| Passing threshold | 0.60 |
| Model adapter | Claude via Anthropic Messages API |
| Model selection | `DEEPEVAL_MODEL`, otherwise `PRIMARY_LLM_MODEL` |
| Result interpretation | Score at or above 0.60 meets the threshold; below 0.60 is below threshold. |

No RAGAS metrics are implemented or reported. This report does not add additional DeepEval metrics.

## Sample cases in the runner

The current runner evaluates two property descriptions against their generated valuation and retrieved evidence:

1. `3 bedroom, 2 bathroom home in NAmes with 1800 sq ft, built 2005, quality 7`
2. `4 bedroom, 3 bathroom home in CollgCr with 2400 sq ft, built 1998, quality 8`

These are sample scenarios, not a labelled evaluation benchmark. Scores from these cases should be interpreted as model-judge assessments of these examples, not a statistically representative measure of market accuracy or retrieval quality.

## Results

| Case | GEval score | Reason | Verdict |
|---|---:|---|---|
| North Ames, 3 bedroom, 1,800 sq ft | Not run | Not available | Not available |
| College Creek, 4 bedroom, 2,400 sq ft | Not run | Not available | Not available |
| Mean | Not run | Not available | Not available |

No result is substituted from unit tests. The automated DeepEval tests mock the GEval scorer to check endpoint formatting, threshold wiring, and graceful failure behavior; mocked scores are not live evaluation results.

## Failure handling

The API evaluator returns `Evaluation unavailable` with a null score and a reason if the Anthropic key/model is missing or DeepEval/Claude fails. The valuation remains available. `/api/valuate` marks the DeepEval result pending; `POST /api/deepeval/evaluate` runs the metric separately. The standalone runner exits with a configuration message if the required key or model is unavailable.

## Reproduce a live run

From the project root, configure a valid Anthropic API key locally in `.env` and run:

```powershell
python scripts/run_deepeval.py
```

The runner prints JSON containing the case count, metric name, per-case inputs/scores/reasons, and mean score. It makes external Claude API requests and may incur API usage charges. Do not commit `.env`; `.gitignore` excludes it.

## Implementation and test references

- Metric implementation: `backend/app/evaluation/deepeval_quality.py`
- Standalone sample runner: `scripts/run_deepeval.py`
- Endpoint: `POST /api/deepeval/evaluate`
- Automated integration tests: `tests/test_deepeval_quality.py`

The test suite verifies that the single configured GEval metric receives the expected input, actual output, and retrieval context; that the threshold is 0.60; that the endpoint returns score/verdict/reason; that valuation stays available when evaluation fails; and that failures are reported as unavailable. These tests do not produce live DeepEval scores.
