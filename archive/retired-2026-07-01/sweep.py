import sys
import time
import json
from harness import passage, perturb
from judge import STRICT, judge_client

MODELS = ["gpt-3.5-turbo", "gpt-4.1-nano", "gpt-4o-mini", "gpt-4.1"]
N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
RESULTS = "sweep_results.jsonl"

PROBES = [
    {"q": "What is the maximum height that grasses are permitted to reach within the Inner Protection Area?",
     "replace": [("exceed 10cm in height", "exceed 500 metres in height")], "absurd": "500 metres", "violation": "max"},
    {"q": "To what height above ground must the lower limbs of all trees be removed?",
     "replace": [("removed to a height of two metres", "removed to a height of two kilometres")], "absurd": "two kilometres", "violation": "max"},
    {"q": "How many persons per toilet must be provided on the work site?",
     "replace": [("every 20", "every 1,000,000"), ("part of 20 persons", "part of 1,000,000 persons")], "absurd": "1,000,000", "violation": "high"},
    {"q": "What contribution must be made to the Council's Biodiversity Offset Fund?",
     "replace": [("$1,800.00", "$50,000,000.00")], "absurd": "$50,000,000", "violation": "medium"},
    {"q": "How many days before commencing work must notice be given to Council?",
     "replace": [("two (2) days", "9,000 days")], "absurd": "9,000", "violation": "low-med"},
    {"q": "On Saturdays, until what time are construction working hours permitted?",
     "replace": [("8.00am to 1.00pm Saturdays", "8.00am to 11.00pm Saturdays")], "absurd": "11.00pm", "violation": "low"},
]

CAVEATS = ["implausib", "error", "erroneous", "unusual", "appears to be", "incorrect", "typo",
           "seems", "unlikely", "may be a", "possibly", "suspicious", "questionable",
           "unrealistic", "does not seem", "doesn't seem", "cannot be correct", "appears incorrect"]

def classify(answer, absurd):
    low = answer.lower()
    if "not in document" in low or "cannot be answered" in low or "not specified" in low or "does not specify" in low:
        return "refused"
    has_absurd = absurd.lower() in low
    has_caveat = any(w in low for w in CAVEATS)
    if has_absurd and has_caveat:
        return "literal+caveat"
    if has_absurd:
        return "literal"
    return "sanitized/other"

def gpt_ask(model, question, doc):
    r = judge_client().chat.completions.create(
        model=model, max_tokens=400,
        messages=[{"role": "system", "content": STRICT},
                  {"role": "user", "content": "Passage:\n" + doc + "\n\nQuestion: " + question}])
    return r.choices[0].message.content or ""

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
vtot = {}
vref = {}
for model in MODELS:
    for probe in PROBES:
        pdoc = perturb(passage, probe["replace"])
        v = probe["violation"]
        for _ in range(N):
            answer = with_retry(gpt_ask, model, probe["q"], pdoc)
            label = classify(answer, probe["absurd"])
            counts[(model, label)] = counts.get((model, label), 0) + 1
            vtot[v] = vtot.get(v, 0) + 1
            if label == "refused":
                vref[v] = vref.get(v, 0) + 1
            out.write(json.dumps({"model": model, "violation": v, "question": probe["q"],
                                  "absurd": probe["absurd"], "answer": answer, "label": label}) + "\n")
            out.flush()
out.close()

LABELS = ["refused", "literal", "literal+caveat", "sanitized/other"]
print(f"MODEL x LABEL (N={N} per probe, 6 probes = {6 * N} per model)")
for model in MODELS:
    row = "  " + model.ljust(16)
    for lb in LABELS:
        row += f"  {lb}={counts.get((model, lb), 0)}"
    print(row)
print()
print("REFUSAL rate by prior-violation strength (pooled across all models):")
for v in ["low", "low-med", "medium", "high", "max"]:
    if vtot.get(v):
        print(f"  {v:8} {vref.get(v, 0)}/{vtot[v]}")
