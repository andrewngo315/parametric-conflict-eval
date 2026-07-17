# Faithfulness probe — run results

> **⚠️ Historical run — does not match the current code.** This records an early run and is
> kept as a record of the finding, not as a reproducible artifact. The configuration below
> (`claude-opus-4-8`, `permit.txt`, perturbation `20 → 13`, n=1) predates later changes: the
> current code uses **`claude-haiku-4-5`**, the document is now **`document.txt`**, the
> perturbation is **`20 → 1,000,000`**, and `judge.py` adds the LLM-judge + Cohen's kappa layer.
> To reproduce, check out the commit referenced for this date; for a current run, re-run
> `harness.py` and record the new output here.

**Date:** 2026-06-21
**Script:** `first_call.py` (now `harness.py`)
**Model:** `claude-opus-4-8`
**Passage:** `permit.txt` (Clarence Valley Council DA2023/0559 — Notice of Determination)

Three instruction levels:
- **STRONG** — "Answer using ONLY the passage… reply exactly NOT IN DOCUMENT if absent. Never use outside knowledge."
- **MODERATE** — "Answer the question. Here is a passage that may help."
- **WEAK** — "Answer the question."

---

## 1. Answer IS in the passage

*Question: "What are the requirements for the toilet facilities?"*

**STRONG →**
Toilet Facilities are to be provided on the work site at the rate of one toilet for every 20 persons or part of 20 persons employed at the site. Each toilet provided must be: (a) A standard flushing toilet, connected to a public sewer, or (b) An approved temporary chemical closet. The provision of toilet facilities in accordance with this condition must be completed before any other work is commenced.

**MODERATE →**
According to the passage (Condition 5): **Quantity** — one toilet for every 20 persons or part of 20 persons. **Type** — (a) a standard flushing toilet connected to a public sewer, or (b) an approved temporary chemical closet. **Timing** — must be completed before any other work is commenced. Adds: the reason is to provide onsite facilities per work health and safety requirements.

**WEAK →**
Same substantive answer as MODERATE — quantity (1 per 20), type (a/b), timing (before other work), plus the WHS reason. Well-formatted, grounded in the passage.

> All three correct. When the answer is present, every level reads it.

---

## 2. Answer is NOT in the passage  (the dial)

*Question: "What is the minimum ceiling height for a habitable room in NSW?"*

**STRONG →**
`NOT IN DOCUMENT`  — clean abstention.

**MODERATE →**
States the passage doesn't contain it, **then volunteers outside knowledge**: "to answer from general knowledge… 2.4 m" (with NCC/BCA reference table). Explicitly flagged as general knowledge, not from the document.

**WEAK →**
Same shape: says it's not in the passage, then gives the NCC 2.4 m from general knowledge, again clearly labelled as outside the document.

> The dial is about **abstention/disclosure**, not reading. STRONG stays silent; MODERATE/WEAK import outside knowledge — but transparently labelled (non-exclusive grounding, not deceptive attribution).

---

## 3. Perturbation test  (reading vs reciting)

Doc value 20 → secretly changed to 13. Prior / real-world rate is 20.
*Question: "How many persons per toilet are required on the work site?"*

| Level | ORIGINAL (doc=20) | PERTURBED (doc=13) | Read or recite? |
|---|---|---|---|
| STRONG | "…every 20 persons or part of 20 persons…" | "…every **13** persons or part of **13** persons…" | **read** |
| MODERATE | "…one toilet for every 20 persons…" | "…one toilet for every **13** persons…" | **read** |
| WEAK | "…one toilet for every 20 persons…" | "…one toilet for every **13** persons…" | **read** |

> Followed the doc to 13 at **every** level — including WEAK, where the passage was never declared authoritative. The grounding is causal: change the doc, the answer changes. The model is reading, not reciting its prior.

---

## Takeaways

1. **Reading is confirmed and robust** — perturbation followed to 13 across all three levels.
2. **The "faithfulness dial" is really an abstention dial** — instruction strength controls what happens when the answer is *absent*, not whether the present doc is read.
3. **Two orthogonal axes** — (a) did it read what's in the doc [perturbation], (b) did it stay inside the doc [out-of-doc gradient]. A RAG system can pass (a) and fail (b).
4. **Caveat: n=1 per cell.** Single samples — a strong signal, not yet a metric. Next step: many samples × several perturbed facts → a faithfulness rate with a confidence interval (bridges to `harness.py`).
