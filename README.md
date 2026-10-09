# AI-Powered Real Estate Property Valuation Assistant

An explainable, local-first valuation microservice for the Ames Housing Dataset. It turns a natural-language property description into ranked historical comparables, a trained-model estimate (or transparent comparable fallback), uncertainty range, risk factors, feature impacts, and evidence.

## PDF requirement mapping

| PDF requirement | Implementation | Demo/test |
|---|---|---|
| Semantic + hybrid similarity search | local semantic vectors, keyword rank, metadata filters, RRF | `POST /api/search` |
| Classification, guardrails, comparables | Pydantic + rule parser + similarity scoring | `tests/test_core.py` |
| Price/risk/feature/location analysis | selected regression model, median fallback, confidence/risk factors | `/api/valuate` |
| Multi-agent collaboration | staged classification/retrieval/valuation/risk/decision workflow | architecture diagram |
| LLM judge and DeepEval | optional, credential-gated entry points | `scripts/run_deepeval.py` |
| Feedback loop | SQLite history/valuation/feedback/evaluation/fallback tables | `/api/feedback` |
| Microservice and frontend | FastAPI and React/Vite dashboard | commands below |
| Architecture/design/panel | `docs/architecture.md`, `docs/demo.md` | Mermaid diagram/demo |

## Dataset and training

The PDF identifies the Ames Housing Dataset (OpenML ID 43926) and requires: `SalePrice`, `OverallQual`, `OverallCond`, `GrLivArea`, `TotalBsmtSF`, `GarageCars`, `GarageArea`, `YearBuilt`, `YearRemodAdd`, `FullBath`, `BedroomAbvGr`, `TotRmsAbvGrd`, `Neighborhood`, `LotArea`, and `GarageYrBlt`. The actual linked OpenML variant uses underscore-separated original field names; `prepare_data.py` normalizes the available fields to these canonical names. Its 2,930-record variant does not contain `GarageYrBlt`, so that field is not used as an ML input.

No dataset was bundled with the brief, so the source-controlled project does not include fabricated rows. Either put the real CSV at `data/AmesHousing.csv`, or use the downloader. The service reports `setup_required` until real data exists and produces no invented valuation/metric.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python scripts/prepare_data.py
python scripts/train_model.py
python scripts/build_embeddings.py
uvicorn backend.app.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173`; API docs are at `http://localhost:8000/docs`.

## API

`POST /api/valuate`, `/api/search`, `/api/compare`, `/api/what-if`, `/api/feedback`, `/api/evaluate`; `GET /api/health`, `/api/model-info`, `/api/config/status`.

Example:

```json
{"query":"3 bedroom, 2 bathroom home in NAmes with 1800 sq ft, built 2005, quality 7"}
```

## LLM-as-Judge setup

Copy `.env.example` to `.env` and add an OpenRouter key plus one or two compatible model identifiers. For example:

```dotenv
OPENROUTER_API_KEY=your_key_here
PRIMARY_LLM_MODEL=your-primary-model-id
FALLBACK_LLM_MODEL=your-fallback-model-id
```

The judge scores groundedness, relevance, completeness, evidence usage, and reasoning quality for the explanation. It receives only the calculated valuation facts and retrieved evidence, uses strict JSON validation, retries the primary once, then tries the fallback model. A judge outage produces a clearly labelled deterministic validation fallback and never alters price, range, confidence, or risk.

## Design notes

Hybrid retrieval metadata-filters candidates, combines a locally calculated semantic vector score and keyword score using reciprocal-rank fusion, then applies property-aware comparable scoring. It first enforces neighborhood/age filters, progressively relaxes them when evidence is sparse, and labels the relaxation. Candidate regressors are evaluated on a holdout split and the lowest-MAE model is saved; no `SalePrice` is included as a feature.

SHAP is used automatically for per-valuation feature impacts through `shap.TreeExplainer` when installed. If it cannot run, the response explicitly labels its deterministic feature-importance fallback. ChromaDB/XGBoost/LangGraph/DeepEval remain optional enhancements because their absence must not stop a laptop-local demo. An LLM is never allowed to alter numerical results and is not invoked without credentials.

Run checks with `python -m pytest`. Evaluation scripts report only measurements they actually calculate. See [architecture](docs/architecture.md) and [demo](docs/demo.md) for the system flow and presentation sequence.
