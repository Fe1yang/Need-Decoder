# Evaluation notes

## Method

All figures below come from the organizer's deterministic evaluator on the 200 labeled public
development sessions. The agent receives only the message, safe aggregate profile, session ID, turn,
and requested result count. Public ground truth is read by the evaluator and diagnostic script, not
by the submitted agent.

The organizer's 800 private sessions use different users and target products. Public results are
development evidence, not a prediction of the final leaderboard.

## Final public result

| Metric | Official BM25 starter | Need Decoder |
| --- | ---: | ---: |
| Hit Rate@10 | 0.125 | **0.990** |
| MRR | 0.068 | **0.610** |
| MTTC | 9.81 | **2.055** |
| Efficiency | 0.119 | **0.8945** |
| Technical Score | 0.107 | **0.8569** |

Scenario Hit Rate@10 is 98.75% for Buying, 98.75% for Browsing, 100% for Intent
Override, and 100% for Boundary sessions.

## Development history

These checkpoints record accumulated changes rather than claiming that a single number explains the
whole improvement.

| Checkpoint | Hit Rate@10 | MRR | MTTC | Technical Score |
| --- | ---: | ---: | ---: | ---: |
| Initial Need Decoder reranker | 0.985 | 0.579 | 2.34 | 0.8393 |
| Feature-aware reranking and safer parsing | 0.985 | 0.590 | 2.27 | 0.8440 |
| Final route and ranking balance | 0.990 | 0.610 | 2.055 | 0.8569 |

The final balance gives feature evidence the same explicit-term weight as title evidence, removes
structured labels such as `color:` before matching their values, and uses review count only through a
logarithm. Attempts to inject profile tags directly into ranking and to broaden the Browsing category
pool both reduced the public score, so neither is present in the final agent.

## Remaining error pattern

The two remaining public misses are broad apparel categories where many products share the same
boilerplate material and closure text. The conversation never reveals a distinctive design or brand,
so the available evidence cannot reliably separate the purchased item from near-duplicates. Raising
the popularity prior further recovered some cases but reduced MRR and recall elsewhere.

## Reproduce

```bash
python3 -m unittest discover -s tests -v
python3 -m evaluator.local_evaluator
```

The full run uses no network calls or model tokens and takes roughly 30–35 seconds in the development
environment. Per-session output is written to `results.json` and is intentionally not committed.
