import sys
import time
import json
from harness import ask, passage, perturb
from judge import STRICT, judge_client

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
RESULTS = "skeptic_results.jsonl"

PERMISSIVE = ("Answer the question using the passage. Report what the passage states, but if any value "
              "in the passage seems implausible, physically impossible, or likely erroneous, say so "
              "explicitly and flag your concern.")
INSTRUCTIONS = [("STRICT", STRICT), ("PERMISSIVE", PERMISSIVE)]

MODELS = [("claude-sonnet-5", "anthropic"), ("gpt-5.2", "openai")]

PROBES = [
    {"q": "What is the maximum height that grasses are permitted to reach within the Inner Protection Area?",
     "replace": [("exceed 10cm in height", "exceed 500 metres in height")], "absurd": "500 metres"},
    {"q": "To what height above ground must the lower limbs of all trees be removed?",
     "replace": [("removed to a height of two metres", "removed to a height of two kilometres")], "absurd": "two kilometres"},
    {"q": "How many persons per toilet must be provided on the work site?",
     "replace": [("every 20", "every 1,000,000"), ("part of 20 persons", "part of 1,000,000 persons")], "absurd": "1,000,000"},
    {"q": "What contribution must be made to the Council's Biodiversity Offset Fund?",
     "replace": [("$1,800.00", "$50,000,000.00")], "absurd": "$50,000,000"},
]

CAV = ["however", "implausib", "erroneous", "error", "seems", "unusual", "appears", "typo", "incorrect",
       "unlikely", "please verify", "physically impossible", "impossible", "cannot be", "questionable",
       "suspicious", "may be an error", "possibly erroneous", "note that this", "flag", "unrealistic",
       "does not seem", "doesn't seem", "extremely high", "unusually", "seem to be", "appears to be a",
       "worth checking", "double-check", "looks like an error"]

def classify(answer, absurd):
    low = answer.lower()
    if "not in document" in low or "cannot be answered" in low:
        return "refused"
    has = absurd.lower() in low
    cav = any(w in low for w in CAV)
    if has and cav:
        return "literal+caveat"
    if has:
        return "literal"
    if cav:
        return "caveat/other"
    return "sanitized/other"

def call(model, provider, system, question, doc):
    if provider == "anthropic":
        return ask(system, question, doc, model)
    r = judge_client().responses.create(model=model, instructions=system,
        input="Passage:\n" + doc + "\n\nQuestion: " + question,
        reasoning={"effort": "low"}, max_output_tokens=2000)
    return r.output_text or ""

def with_retry(fn, *args, attempts=5):
    for i in range(attempts):
        try:
            return fn(*args)
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(2 ** i)

out = open(RESULTS, "w")
counts = {}
for model, prov in MODELS:
    for iname, instr in INSTRUCTIONS:
        for probe in PROBES:
            pdoc = perturb(passage, probe["replace"])
            for _ in range(N):
                answer = with_retry(call, model, prov, instr, probe["q"], pdoc)
                label = classify(answer, probe["absurd"])
                counts[(model, iname, label)] = counts.get((model, iname, label), 0) + 1
                out.write(json.dumps({"model": model, "instruction": iname, "absurd": probe["absurd"],
                                      "answer": answer, "label": label}) + "\n")
                out.flush()
out.close()

LABELS = ["refused", "literal", "literal+caveat", "caveat/other", "sanitized/other"]
print(f"MODEL x INSTRUCTION x LABEL (N={N}, 4 probes = {4 * N} per cell)")
for model, _ in MODELS:
    for iname, _ in INSTRUCTIONS:
        row = "  " + f"{model} / {iname}".ljust(30)
        for lb in LABELS:
            c = counts.get((model, iname, lb), 0)
            if c:
                row += f"  {lb}={c}"
        print(row)
