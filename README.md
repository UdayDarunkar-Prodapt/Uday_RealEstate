# AI-Powered Real Estate Property Valuation Assistant

An explainable, local-first valuation microservice for the Ames Housing Dataset. It turns a natural-language property description into ranked historical comparables, a trained-model estimate (or transparent comparable fallback), uncertainty range, risk factors, feature impacts, and evidence.

## Mandatory deliverables

| Deliverable | File/location |
|---|---|
| Architecture diagram (PDF) | [Architecture diagram](docs/architecture.pdf), source [architecture.md](docs/architecture.md) |
| Design document (PDF) | [Design document](docs/design_document.pdf), source [design_document.md](docs/design_document.md) |
| Complete source code | Backend `backend/`, frontend `frontend/`, scripts `scripts/`, tests `tests/` |
| README | This file |
| API documentation | [API reference PDF](docs/API_Documentation.pdf) and [Markdown source](docs/API_Documentation.md), plus live Swagger at `/docs` |
| Dataset details | [Dataset details PDF](docs/data_details.pdf) and [Markdown source](docs/data_details.md) |
| DeepEval evaluation report | [DeepEval report PDF](docs/DeepEval_Evaluation_Report.pdf) and [Markdown source](docs/DeepEval_Evaluation_Report.md) |

Regenerate the PDFs from the repository root:

```powershell
python scripts/build_architecture_pdf.py
python scripts/build_design_document_pdf.py
python scripts/build_reference_pdfs.py
python scripts/build_deepeval_report_pdf.py
```

## Requirement mapping

| PDF requirement | Implementation | Demo/test |
|---|---|---|
| Semantic + hybrid similarity search | Chroma vectors, BM25Okapi, location/age/room/size metadata filters, RRF | `POST /api/search` |
| Classification, guardrails, comparables | Pydantic bounds, instruction-pattern checks, feature extraction, progressive filter relaxation | `tests/test_core.py` |
| Price/risk/feature/location analysis | selected regression model, evidence-based risk score, SHAP and historical location context | `/api/valuate` |
| Multi-agent collaboration | LangGraph specialist stages share one typed state and evidence | [architecture diagram](docs/architecture.pdf) |
| LLM judge and DeepEval | grounded judge plus DeepEval recommendation-quality runner | `scripts/run_deepeval.py` |
| Feedback loop | SQLite ratings add a small comparable-ranking prior after three votes | `/api/feedback` and dashboard |
| Microservice and frontend | FastAPI and React/Vite dashboard | commands below |
| Architecture/design/panel | `docs/architecture.md`, `docs/design_document.md`, `docs/demo.md` | PDF diagrams and demo |

## Dataset and training

The project includes `data/AmesHousing.csv` (2,930 rows, 81 columns). OpenML ID 43926 is the upstream dataset source. `prepare_data.py` normalizes source fields and preserves `GarageYrBlt` when supplied; training includes it only when present. This local CSV lacks that field. See [dataset details](docs/data_details.md) for source attribution, inspected local data profile, preparation, and limitations.

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

`sentence-transformers` downloads `sentence-transformers/all-MiniLM-L6-v2` the first time the local index is built. The model then runs locally and is cached; no embedding API or OpenAI key is used. Rebuild Chroma after changing the dataset or embedding model with:

```powershell
python scripts/build_embeddings.py
```

## API

`POST /api/valuate`, `/api/search`, `/api/compare`, `/api/what-if`, `/api/feedback`, `/api/evaluate`, `/api/deepeval/evaluate`; `GET /api/health`, `/api/model-info`, `/api/config/status`. See [API documentation](docs/API_Documentation.md) or its [PDF](docs/API_Documentation.pdf) for payloads and response behavior.

Example:

```json
{"query":"3 bedroom, 2 bathroom home in NAmes with 1800 sq ft, built 2005, quality 7"}
```

With the included Ames dataset and trained model, that query currently returns an estimated **$208,313**, a **$187,202-$229,425** range, and five North Ames comparables. Values can change if the dataset or model is rebuilt. The response also includes the historical neighborhood median difference and whether any filters were relaxed; the location difference is descriptive, not causal.

## LLM-as-Judge setup

Add your Anthropic Console API key to the project root `.env`. The valuation API uses Claude Sonnet 4.6 as the default judge model; you can override it or configure a fallback model:

```dotenv
ANTHROPIC_API_KEY=your_anthropic_key_here
PRIMARY_LLM_MODEL=claude-sonnet-4-6
FALLBACK_LLM_MODEL=
DEEPEVAL_MODEL=claude-sonnet-4-6
```

The `/api/valuate` and `/api/evaluate` endpoints call Anthropic's Messages API when `ANTHROPIC_API_KEY` is set. The judge scores groundedness, relevance, completeness, evidence usage, and reasoning quality for the explanation. It receives only calculated valuation facts and retrieved evidence, validates the returned JSON, retries once, then tries the optional fallback model. A judge outage produces a clearly labelled deterministic validation fallback and never alters price, range, confidence, or risk. Check `/api/config/status` for `external_llm_configured: true`; restart the backend after editing `.env`. `python scripts/run_deepeval.py` also uses the Claude key and runs DeepEval's recommendation-quality metric on live sample valuations. Claude API usage is billed by Anthropic; embeddings remain local and do not use Claude or an embedding API.

## Design notes

Hybrid retrieval uses normalized `sentence-transformers/all-MiniLM-L6-v2` embeddings in Chroma's persistent cosine index and `BM25Okapi` for lexical ranking, then combines both ranked lists with reciprocal-rank fusion before property-aware comparable scoring. It filters by neighborhood, year, bedrooms, bathrooms, rooms, and living/lot area, progressively relaxing constraints when evidence is sparse. If Chroma is unavailable, MiniLM semantic search runs locally against cached document vectors; if MiniLM itself cannot load, BM25 remains as the final retrieval fallback. Repeated feedback can only make a small ranking adjustment after three ratings; it never changes valuation numbers. Candidate regressors are evaluated on a holdout split and the lowest-MAE model is saved; no `SalePrice` is included as a feature. Risk is an evidence-based score built from match quality, input completeness, model availability, and comparable price spread, not a separate trained risk model.

SHAP is used automatically for per-valuation feature impacts through `shap.TreeExplainer` when installed. The response also includes an observed neighborhood sale-price median difference when location is known, clearly labelled descriptive rather than causal. If SHAP cannot run, the response labels its deterministic feature-importance fallback. ChromaDB and LangGraph are optional dependencies: when present, Chroma checks and rebuilds its local index on service startup, and LangGraph runs the specialist workflow. Their status is exposed by `/api/health`; without them, deterministic local retrieval and pipeline fallbacks remain available. An LLM is never allowed to alter numerical results and is not invoked without credentials.

Run checks with `python -m pytest`. Evaluation scripts report only measurements they actually calculate. See [architecture](docs/architecture.md) and [demo](docs/demo.md) for the system flow and presentation sequence.
