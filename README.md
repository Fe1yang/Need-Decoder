# Need Decoder

Need Decoder is a conversational product search agent for TikTok TechJam 2026, Track 4.
It is built around a simple observation: shoppers are usually better at describing their situation
than writing the perfect search query.

If someone asks for shoes for a company retreat, the useful clues are not just *shoes* and
*retreat*. They may need something comfortable for walking, presentable at dinner, and dependable
outdoors. Need Decoder keeps the shopper's explicit constraints separate from those inferred needs,
records why each inference was made, and uses both to retrieve products. Explicit requirements
always win.

The agent runs offline and implements the organizer's required `Agent` interface. It does not need
an API key, hosted model, vector database, or network connection during evaluation.

## Development result

The table below is from the organizer's deterministic evaluator on all 200 labeled public sessions.
The private 800-session set is held by the organizer, so these numbers are development results rather
than a claim about the final ranking.

| Metric | Official BM25 starter | Need Decoder |
| --- | ---: | ---: |
| Hit Rate@10 | 0.125 | **0.985** |
| MRR | 0.068 | **0.579** |
| MTTC (lower is better) | 9.81 | **2.34** |
| Efficiency | 0.119 | **0.866** |
| Technical Score | 0.107 | **0.839** |

Scenario-level Hit Rate@10: Buying 98.75%, Browsing 98.75%, Intent Override 96.67%, and Boundary 100%.

## How it works

The runtime has four small components:

1. `ConversationState` separates category, explicit constraints, inferred needs, asked attributes,
   and intent. An override replaces the earlier preference without throwing away useful answers to
   later clarification questions.
2. The hidden-needs layer maps situational evidence to low-weight, explainable hypotheses. A
   hypothesis contains an attribute, value, confidence, and the evidence behind it.
3. The question policy requests the attribute most likely to reduce uncertainty. It supports
   incremental slots—for example, asking whether there is another material requirement after the
   shopper has already mentioned leather. Aggregate profile tags can change the order of later
   questions, but they are never treated as hard product constraints.
4. `CatalogSearch` narrows the 50,000-item catalog by category with SQLite FTS5, retrieves evidence
   matches, and reranks candidates using field weights, inverse document frequency, exact constraint
   coverage, and a weak popularity prior.

The inferred terms have a deliberately small weight. They can help distinguish otherwise similar
items, but cannot override a stated color, material, size, or use case.

More detail is in [the architecture note](docs/need_decoder_architecture.md).

## Repository layout

```text
need_decoder/                 state, inference, question policy, retrieval
starter/agent.py              official competition adapter
evaluator/local_evaluator.py  organizer's public evaluator
scripts/inspect_public_session.py
                              labeled development diagnostics
tests/                        contract, state, text, and evaluator tests
demo.py                       short end-to-end demonstration
```

## Setup

Python 3.10 or newer is recommended. The core agent uses only the Python standard library.

Download `catalog.jsonl.gz` from the official
[participant-kit release](https://github.com/TechJam2026/techjam-conversational-search/releases/tag/participant-kit),
then verify and extract it:

```bash
sha256sum data/catalog.jsonl.gz
# Expected: 07fd142631fd6b03e2b4d09988c3eb7d53720e9d57010c79db48eeaada50a8f8

gzip -dk data/catalog.jsonl.gz
```

Place the extracted file at `data/catalog.jsonl`. The catalog is intentionally not committed to this
repository; it remains available from the organizer's release.

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

Run the official public evaluator:

```bash
python3 -m evaluator.local_evaluator
```

It writes the per-session output to `results.json`.

Run the human-readable demo:

```bash
python3 demo.py
```

To inspect one labeled public development session turn by turn:

```bash
python3 -m scripts.inspect_public_session public_0026
```

That diagnostic script is not imported by the agent and is never used at inference time.

## Cost and runtime

- Model/API cost: **$0**
- Network access during inference: **none**
- Reported model tokens: **0**
- External Python packages required by the agent: **none**
- Full 200-session evaluation in the current development environment: roughly **30–35 seconds**

The catalog index is built once when the agent starts. Search results and tokenized candidate fields
are cached for the lifetime of the process.

## Known limitations

Hidden-need inference currently uses a small, auditable context rule set. It handles common signals
such as weather, walking, professional settings, gifts, and social occasions, but it will not infer
every niche requirement. The deterministic design is useful for a three-day build because it is
cheap, reproducible, and easy to debug; a production version should compare it with a calibrated
semantic model on consented interaction data.

The popularity feature is intentionally weak, but it can still favor established products when the
conversation leaves several candidates indistinguishable. Price parsing and negative constraints
are the next areas to strengthen.

## Data attribution

The frozen catalog and sessions are derived from Amazon Reviews 2023 by McAuley Lab, UCSD. See
[DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md) and the organizer's
[competition repository](https://github.com/TechJam2026/techjam-conversational-search).

## Participant and contribution

**Yu Feiyang** is the sole participant and built the project end to end: product concept, system
design, implementation, testing, evaluation, documentation, and demo.
