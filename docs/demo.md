# 10-minute panel demo

1. Start backend and frontend (README commands).
2. Enter the default NAmes query and submit it.
3. Point out extracted features, calculated estimate/range, risk, and retrieval mode.
4. Open comparable rows to explain the ranked historical evidence.
5. Highlight the feature-impact section and state whether its fallback label is present.
6. Call `POST /api/what-if` in Swagger with `{"property":{"query":"..."},"changes":{"GrLivArea":2200}}` and explain it is model-based, not causal.
7. Rate the evidence in the dashboard. SQLite stores the rating; once a comparable has three ratings, that feedback can make a small ranking adjustment on later searches. It never changes predicted prices.
8. Run `python scripts/run_deepeval.py` with judge credentials to show actual recommendation-quality scores.
9. Demonstrate resilience by stopping/renaming the model file: the response transparently switches to the comparable-median fallback.
