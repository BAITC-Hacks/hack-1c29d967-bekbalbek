# Evaluation suite

```bash
make eval                      # scripted model: deterministic, no API key, ~10s
EVAL_MODEL=live make eval      # real model from OPENAI_MODEL; needs OPENAI_API_KEY
EVAL_ONLY=stale_proposal,duplicate_apply make eval
```

Each scenario reseeds the sample data in a separate `agent_workspace_eval` database, runs the full pipeline through the same services the API uses, and checks the business outcome directly in PostgreSQL (assignment rows, job statuses, per-day load). The runner records status/outcome, violated constraints, final-state correctness, wall-clock duration, tool-call count and token usage, prints a table, and saves JSON under `evals/results/`.

Scripted mode uses canned agent conversations from `app/domain/scripts.py`; the validator, executor and verifier are the real ones. Live mode replaces only the model.
