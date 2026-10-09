# 10-minute panel demo

1. Start backend and frontend (README commands).
2. Enter the default NAmes query and submit it.
3. Point out extracted features, calculated estimate/range, risk, and retrieval mode.
4. Open comparable rows to explain the ranked historical evidence.
5. Highlight the feature-impact section and state whether its fallback label is present.
6. Call `POST /api/what-if` in Swagger with `{"property":{"query":"..."},"changes":{"GrLivArea":2200}}` and explain it is model-based, not causal.
7. Submit feedback through `/api/feedback`; SQLite retains it.
8. Demonstrate resilience by stopping/renaming the model file: the response transparently switches to the comparable-median fallback.
