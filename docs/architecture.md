# Architecture and decisions

```mermaid
flowchart TD
U[Real-estate professional] --> R[React dashboard] --> A[FastAPI guardrails]
A --> G[Orchestrated valuation workflow]
G --> C[Classification: structured + rule fallback]
G --> H[Hybrid retrieval]
H --> M[Metadata filters] & V[Local semantic vectors] & B[BM25-style keyword rank]
M & V & B --> F[RRF + comparable scoring]
F --> P[Model prediction]
P --> X[SHAP / feature-importance fallback]
F --> K[Risk & confidence]
X & K --> D[Grounded decision response]
D --> J[Optional LLM + judge]
A --- S[(SQLite: history, feedback, evaluations, fallback events)]
P -. failure .-> Q[Comparable median fallback]
H -. failure .-> L[Broadened structured search]
J -. failure .-> D
```

The app deliberately uses local SQLite and local retrieval so it stays usable without cloud services. LLM and Chroma enhancements are optional; their absence is disclosed rather than hidden. The active implementation performs deterministic orchestration with independently recoverable classification, retrieval, prediction, risk, and explanation stages; LangGraph can be added as an execution backend when installed without changing state boundaries.
