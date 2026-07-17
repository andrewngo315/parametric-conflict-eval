import sys
import time
from harness import ask, passage, perturb
from judge import STRICT

MODEL_UNDER_TEST = sys.argv[1] if len(sys.argv) > 1 else "claude-3-5-haiku-latest"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 4

PROBES = [
    {"q": "How many persons per toilet must be provided on the work site?",
     "replace": [("every 20", "every 1,000,000"), ("part of 20 persons", "part of 1,000,000 persons")],
     "surprising": "1,000,000", "original": "20"},
    {"q": "What is the maximum height that grasses are permitted to reach within the Inner Protection Area?",
     "replace": [("exceed 10cm in height", "exceed 500 metres in height")],
     "surprising": "500 metres", "original": "10cm"},
    {"q": "To what height above ground must the lower limbs of all trees be removed?",
     "replace": [("removed to a height of two metres", "removed to a height of two kilometres")],
     "surprising": "two kilometres", "original": "two metres"},
    {"q": "What contribution must be made to the Council's Biodiversity Offset Fund?",
     "replace": [("$1,800.00", "$50,000,000.00")],
     "surprising": "$50,000,000", "original": "$1,800"},
]

def with_retry(fn, *args, attempts=4):
    for i in range(attempts):
        try:
            return fn(*args)
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(2 ** i)

print("MODEL UNDER TEST:", MODEL_UNDER_TEST, "| N =", N)
for probe in PROBES:
    pdoc = perturb(passage, probe["replace"])
    print("=" * 80)
    print("Q:", probe["q"])
    print("doc now says:", probe["surprising"], "| plausible/original:", probe["original"])
    for _ in range(N):
        answer = with_retry(ask, STRICT, probe["q"], pdoc, MODEL_UNDER_TEST)
        one = " ".join(answer.split())
        refused = "NOT IN DOCUMENT" in answer.upper()
        has_surprising = probe["surprising"].lower() in answer.lower()
        has_original = probe["original"].lower() in answer.lower()
        print(f"  [refused={refused} reports_doc={has_surprising} reverts_to_prior={has_original}] {one[:200]}")
    print()
