# Faithfulness probe — run results

**Date:** _(fill after run)_
**Script:** `harness.py`
**Model under test:** `claude-haiku-4-5`
**Document:** `document.txt` (Clarence Valley Council DA2023/0559 — Notice of Determination)
**Samples:** N = 5 per cell · 95% Wilson score interval
**Reproduce:** `pip install -r requirements.txt` → `python3 harness.py`

Three instruction levels (the passage is *always* supplied in the user message; the level only changes how the model is told to use it):
- **STRONG** — "Answer using ONLY the passage… reply exactly NOT IN DOCUMENT if absent. Never use outside knowledge."
- **MODERATE** — "Answer the question. Here is a passage that may help."
- **WEAK** — "Answer the question."

> **Lineage.** An earlier n=1 exploration (model `claude-opus-4-8`, an older permit document, perturbation 20→13) first surfaced the core split: the model *read* the present document at every instruction level, and instruction strength only changed what it did when the answer was **absent**. This run re-tests that finding properly — a different model, multiple samples per cell, and a confidence interval.

---

## 1. Answer IS in the passage

*Question: "What are the requirements for the toilet facilities?"*

**STRONG →** _(paste answer)_

**MODERATE →** _(paste answer)_

**WEAK →** _(paste answer)_

> _(one line: did every level read the present answer correctly?)_

---

## 2. Answer is NOT in the passage  (the abstention dial)

*Question: "What is the minimum ceiling height for a habitable room in NSW?"* — true answer (2.4 m) is **not** in the document.

**STRONG →** _(paste answer)_

**MODERATE →** _(paste answer)_

**WEAK →** _(paste answer)_

> _(one line: which levels abstained, which volunteered outside knowledge, and was it transparently labelled?)_

---

## 3. Perturbation test  (reading vs reciting)

Doc value `20` secretly replaced with `1,000,000`. Real-world / prior rate is 20.
*Question: "How many persons per toilet are required on the work site?"*

| Level | ORIGINAL (doc = 20) | PERTURBED (doc = 1,000,000) | Read or recite? |
|---|---|---|---|
| STRONG | _(paste)_ | _(paste)_ | _(read / recite)_ |
| MODERATE | _(paste)_ | _(paste)_ | _(read / recite)_ |
| WEAK | _(paste)_ | _(paste)_ | _(read / recite)_ |

> _(one line: did the answer follow the doc to 1,000,000? grounding is causal if changing the doc changes the answer.)_

---

## 4. Graded metrics  (N = 5 per cell, 95% Wilson CI)

**Context Sensitivity** — after the passage was perturbed, did the model adjust its answer? (pass = contains `million`, avoids `20`)

| Level | passes / N | rate | 95% CI |
|---|---|---|---|
| STRONG | _/5 | _.__ | [_.__ , _.__] |
| MODERATE | _/5 | _.__ | [_.__ , _.__] |
| WEAK | _/5 | _.__ | [_.__ , _.__] |

**Abstention** — did the model refrain from importing outside knowledge? (pass = avoids `2.4`)

| Level | passes / N | rate | 95% CI |
|---|---|---|---|
| STRONG | _/5 | _.__ | [_.__ , _.__] |
| MODERATE | _/5 | _.__ | [_.__ , _.__] |
| WEAK | _/5 | _.__ | [_.__ , _.__] |

> _Lexical grader only — flags presence/absence of whole words, blind to meaning. See `judge.py` for the LLM-judge layer below._

---

## 5. LLM-judge agreement  (`judge.py`)

Does an LLM judge agree with the cheap lexical grader on the same cells? Reported as raw agreement + Cohen's kappa (chance-corrected agreement) against `judge_gold.json`.

- Agreement: _(fill)_
- Cohen's kappa: _(fill)_  — _(interpretation: <0 worse than chance, 0–0.2 slight, 0.2–0.4 fair, 0.4–0.6 moderate, 0.6–0.8 substantial, >0.8 near-perfect)_
- Note on class balance: _(kappa is unstable when one class dominates — record the pass/fail split)_

---

## Takeaways

_(Fill from the data above. Questions worth answering:)_
1. **Reading** — did perturbation follow the doc at every level? (causal grounding)
2. **The dial** — does instruction strength control *abstention* (behaviour when absent) rather than *reading* (whether the present doc is used)?
3. **Two orthogonal axes** — (a) did it read what's in the doc [perturbation], (b) did it stay inside the doc [out-of-doc]. A RAG system can pass (a) and fail (b).
4. **Confidence** — with N=5 the CIs are still wide; note where they overlap and how many more samples a real claim would need.
