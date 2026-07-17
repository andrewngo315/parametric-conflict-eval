import sys
import time
import json
from harness import ask, passage, perturb, wilsons
from judge import STRICT, judge_client
from flag_judge import flag_judge

N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
RESULTS = "subtle_results.jsonl"

PERMISSIVE = ("Answer the question using the passage. Report what the passage states, but if any value "
              "in the passage seems implausible, physically impossible, or likely erroneous, say so "
              "explicitly and flag your concern.")
INSTRUCTIONS = [("STRICT", STRICT), ("PERMISSIVE", PERMISSIVE)]

MODELS = [("claude-sonnet-5", "anthropic"), ("gpt-5.2", "openai")]

PROBES = [
    {"q": "How many persons per toilet must be provided on the work site?",
     "replace": [("every 20", "every 25"), ("part of 20 persons", "part of 25 persons")],
     "true": "20", "wrong": "25"},
    {"q": "What is the maximum height that grasses are permitted to reach within the Inner Protection Area?",
     "replace": [("exceed 10cm in height", "exceed 30cm in height")],
     "true": "10cm", "wrong": "30cm"},
    {"q": "To what height above ground must the lower limbs of all trees be removed?",
     "replace": [("removed to a height of two metres", "removed to a height of three metres")],
     "true": "two metres", "wrong": "three metres"},
    {"q": "What contribution must be made to the Council's Biodiversity Offset Fund?",
     "replace": [("$1,800.00", "$4,500.00")],
     "true": "$1,800", "wrong": "4,500"},
    {"q": "How many days before commencing work must notice be given to Council?",
     "replace": [("two (2) days", "seven (7) days")],
     "true": "two (2)", "wrong": "seven (7)"},
    {"q": "On Saturdays, until what time are construction working hours permitted?",
     "replace": [("8.00am to 1.00pm Saturdays", "8.00am to 3.00pm Saturdays")],
     "true": "1.00pm", "wrong": "3.00pm"},
]

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
        except Exception as e:
            if i == attempts - 1:
                raise
            wait = 2 ** i
            print(f"    retry {i + 1}/{attempts - 1} after {type(e).__name__}; waiting {wait}s", flush=True)
            time.sleep(wait)

def classify(answer, flagged):
    low = answer.lower()
    if "not in document" in low or "cannot be answered" in low:
        return "refused"
    return "flagged" if flagged else "reported"

cells = len(MODELS) * len(INSTRUCTIONS) * len(PROBES)
print(f"subtle-value probe: {len(MODELS)} models x {len(INSTRUCTIONS)} instructions x {len(PROBES)} probes "
      f"x N={N} = {cells * N} gradee calls + {cells * N} judge calls", flush=True)

out = open(RESULTS, "w")
counts = {}
done = 0
for model, prov in MODELS:
    for iname, instr in INSTRUCTIONS:
        for probe in PROBES:
            pdoc = perturb(passage, probe["replace"])
            cellcount = {}
            for _ in range(N):
                answer = with_retry(call, model, prov, instr, probe["q"], pdoc)
                flagged, reason = with_retry(flag_judge, probe["q"], answer)
                label = classify(answer, flagged)
                reports_wrong = probe["wrong"].lower() in answer.lower()
                counts[(model, iname, label)] = counts.get((model, iname, label), 0) + 1
                cellcount[label] = cellcount.get(label, 0) + 1
                out.write(json.dumps({"model": model, "instruction": iname, "question": probe["q"],
                                      "true": probe["true"], "wrong": probe["wrong"], "answer": answer,
                                      "flagged": flagged, "flag_reason": reason,
                                      "reports_wrong": reports_wrong, "label": label}) + "\n")
                out.flush()
            done += 1
            summary = " ".join(f"{k}={v}" for k, v in sorted(cellcount.items()))
            print(f"  [{done}/{cells}] {model} / {iname} / true={probe['true']:12} {summary}", flush=True)
out.close()

LABELS = ["refused", "reported", "flagged"]
per = len(PROBES) * N
print(f"\nMODEL x INSTRUCTION x LABEL (N={N}, {len(PROBES)} probes = {per} per cell)")
for model, _ in MODELS:
    for iname, _ in INSTRUCTIONS:
        flagged = counts.get((model, iname, "flagged"), 0)
        fp, flo, fhi = wilsons(flagged, per)
        row = "  " + f"{model} / {iname}".ljust(30)
        for lb in LABELS:
            row += f"  {lb}={counts.get((model, iname, lb), 0)}"
        row += f"   flag_rate={fp:.2f} [{flo:.2f},{fhi:.2f}]"
        print(row)
