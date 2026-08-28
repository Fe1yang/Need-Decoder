# Need Decoder — Devpost draft

## Inspiration

Most shopping search assumes the customer already knows how to describe the right product. In
practice, people start with a situation: a company retreat, a gift for someone they do not know well,
or an outfit that has to work in hot weather and a formal room. The details that determine whether a
purchase works are often left unsaid.

We built Need Decoder to make those missing details visible without turning shopping into a long
questionnaire.

## What it does

Need Decoder routes each conversation as Buying or Browsing, keeps a structured record of explicit
constraints, and derives low-confidence hidden-need hypotheses from situational evidence. It asks one
focused follow-up question while returning a ranked Top 10 on every turn.

When a customer changes their mind, the agent replaces the stale preference but keeps useful answers
to independent clarification questions. Each hidden need includes the evidence and confidence behind
it, so the behavior can be explained in a demo rather than hidden inside a prompt.

## How we built it

The agent is written in Python and runs offline. SQLite FTS5 indexes the frozen 50,000-product Amazon
Reviews 2023 catalog in memory. Retrieval follows separate category and evidence paths. A deterministic
reranker combines field-aware lexical coverage, IDF, exact constraint coverage, low-weight inferred
needs, and a weak popularity prior.

The implementation follows the organizer's `reset`/`respond` API exactly and uses no paid model,
external database, or hosted service. Tests cover the response contract, negative replies, question
progression, state overrides, and evaluator behavior.

## Results

On the organizer's 200 labeled public sessions:

- Hit Rate@10: 0.985
- MRR: 0.579
- MTTC: 2.34 turns
- Technical Score: 0.839

The official BM25 starter records 0.125 Hit Rate@10, 0.068 MRR, and 9.81 MTTC on the same set. The
private set is not available to participants, so we treat the public result as development evidence,
not a final-set guarantee.

## Tools and data

- Python 3.10+
- SQLite FTS5
- `unittest`
- Organizer-provided participant kit and deterministic evaluator
- Frozen 50,000-product catalog derived from Amazon Reviews 2023

No external API is required by the submitted agent.

## Challenges

The hardest state bug appeared during an intent override. A full reset removed the old preference,
but it also discarded valid constraints collected through earlier questions. Preserving everything
had the opposite problem. We changed the implementation to replace the opening preference while
retaining independently collected constraints, then reopen the clarification plan for the new goal.

Retrieval also had to balance recall against latency. A broad evidence-only route added little to the
public score but tripled evaluation time. Restricting it to conversations without a usable category
kept Hit Rate@10 at 98.5% and reduced the 200-session run from roughly 90 seconds to about 34 seconds in our
development environment.

## Limitations and next steps

The hidden-needs rules cover common shopping contexts, not every niche use case. Price ranges and
negative requirements need more structured handling. With more time, we would compare the current
offline reranker against a small calibrated semantic model, evaluate inference quality with human
annotations, and add a consented long-term profile rather than treating every session in isolation.

## Team contributions

Add each registered team member and their concrete contribution before submission.
