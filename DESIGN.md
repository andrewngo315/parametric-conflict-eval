# Design note — wiring the LLM judge into the harness

## Problem
`harness.py` grades faithfulness with `grade()` — whole-word lexical matching, which is
semantically blind (it can be fooled by paraphrase, implication, or a forbidden value that
appears in an unrelated context). `judge.py` contains a *validated* semantic judge, but it
only validates itself against human labels (Cohen's kappa) and is **not wired into the
harness as a grader**. This note records how we connect them.

## Goal
Run the semantic judge as a **second grader on the abstention axis**, next to the lexical
check, on the **same** model answers — so the harness surfaces exactly where word-matching
and a meaning-aware judge disagree. That disagreement is the demonstration of why lexical
grading alone is insufficient.

## Decisions
1. **Augment, don't replace.** Keep the lexical grader; show both rates side by side. The
   judge's value is only legible against the lexical baseline.
2. **Judge all N samples** (not once), so it gets its own Wilson CI directly comparable to
   the lexical row. ~15 extra judge calls per full run (N=5 × 3 levels × 1 abstention probe).
3. **Abstention axis only.** The judge's prompt assumes "the passage does not contain the
   answer", so it structurally cannot grade the perturbation/context-sensitivity axis. Axis 1
   stays lexical-only; only axis 2 gets the dual grader.
4. **Generate once, grade twice.** Both graders must score *identical* answers, or a
   disagreement conflates grader differences with model-output differences. `measure()` is
   refactored to generate the N answers once, then score that list lexically and (optionally)
   with the judge.
5. **Surface disagreement.** Per cell print a lexical row and a judge row; collect every
   sample where the two verdicts split and dump the answer text + the judge's reason
   afterwards (mirrors the disagreement display already in `judge.py`).
6. **Guard the OpenAI key, don't hard-require it.** If `OPENAI_API_KEY` is absent, the
   harness runs lexical-only and prints a skip notice. Preserves the property that
   import/tests/lexical runs need no OpenAI key.
7. **No hard validation gate.** The judge used here is the same model validated in
   `judge.py`; we print a one-line caveat rather than reading a kappa file to gate use.

## Scope boundaries
- Does not touch axis-1 (perturbation) grading.
- Does not modify `judge.py` — only imports `judge()` from it (new edge: harness → judge; no
  cycle, since `judge.py` imports neither).
- Does not auto-validate the judge before use.

## Footprint
+~15 OpenAI calls per full run; new import edge harness→judge; harness gains an optional
second key. `test_logic.py` is unaffected — it tests pure logic, and the judge path is guarded.
