# Need Decoder — Devpost draft

## Inspiration

Most shopping search assumes the customer already knows how to describe the right product. In
practice, people start with a situation: a company retreat, a gift for someone they do not know well,
or an outfit that has to work in hot weather and a formal room. The details that determine whether a
purchase works are often left unsaid.

I built Need Decoder to make those missing details visible without turning shopping into a long
questionnaire.

## What it does

Need Decoder routes each conversation as Buying or Browsing, keeps explicit requirements separate
from inferred needs, and understands common budgets and exclusions. It asks one focused follow-up
question while returning a ranked Top 10 on every turn.

When a customer changes their mind, the agent replaces the stale preference but keeps useful answers
to independent clarification questions. Each hidden need includes the evidence and confidence behind
it, so the behavior can be explained in a demo rather than hidden inside a prompt.

## How I built it

The agent is written in Python and runs offline. SQLite FTS5 indexes the frozen 50,000-product Amazon
Reviews 2023 catalog in memory. Buying and Browsing use different evidence ordering and candidate
limits while sharing a category safety route. A deterministic reranker combines field-aware lexical
coverage, IDF, exact constraints, price compatibility, exclusions, low-weight inferred needs, and a
log-scaled popularity fallback.

The implementation follows the organizer's `reset`/`respond` API exactly and uses no paid model,
external database, or hosted service. The current suite contains 23 tests covering the response
contract, budgets, exclusions, natural request phrasing, question progression, state overrides,
retrieval, and evaluator behavior.

## Results

On the organizer's 200 labeled public sessions:

- Hit Rate@10: 0.990
- MRR: 0.610
- MTTC: 2.06 turns
- Efficiency: 0.895
- Technical Score: 0.857

The official BM25 starter records 0.125 Hit Rate@10, 0.068 MRR, and 9.81 MTTC on the same set. The
private set is not available to participants, so I treat the public result as development evidence,
not a final-set guarantee.

## Why it matters

Customers often know the situation they are buying for but not the catalog vocabulary that describes
the right product. Making those missing requirements visible can reduce repeated searches and avoid
recommendations that technically match a keyword but fail in real use. The inference record also
gives a product team something concrete to inspect instead of hiding the decision inside a prompt.

The current implementation is inexpensive enough to run as a first-stage commerce service or on a
developer laptop. A production system could keep this deterministic layer as a fallback around a
calibrated semantic model.

## Tools and data

- Python 3.10+
- SQLite FTS5
- `unittest`
- GitHub Actions
- Organizer-provided participant kit and deterministic evaluator
- Frozen 50,000-product catalog derived from Amazon Reviews 2023

No external API is required by the submitted agent.

## Challenges

The hardest state bug appeared during an intent override. A full reset removed the old preference,
but it also discarded valid constraints collected through earlier questions. Preserving everything
had the opposite problem. I changed the implementation to replace the opening preference while
retaining independently collected constraints, then reopen the clarification plan for the new goal.

Retrieval also had to balance recall against latency. A broad evidence-only route added little to the
public score but tripled evaluation time. Restricting it to conversations without a usable category
kept recall high and reduced the 200-session run from roughly 90 seconds to about 30–35 seconds in my
development environment.

Another issue was field bias. Product titles often repeat category words, while the evaluator's
requirements frequently come from the feature field. Giving title and feature evidence equal weight,
then keeping popularity log-scaled, improved the combined public Technical Score without changing the
Agent contract or adding network calls.

## Limitations and next steps

The hidden-needs rules cover common shopping contexts, not every niche use case. Budget and exclusion
parsing handles common English forms but is not a full semantic parser. With more time, I would compare
the offline reranker against a small calibrated semantic model, evaluate inference quality with human
annotations, and test consented longer-term preferences without turning them into hard constraints.

## Participant and contribution

**Yu Feiyang** is the sole participant and is responsible for the project concept, system design,
implementation, testing, evaluation, documentation, and demo.
