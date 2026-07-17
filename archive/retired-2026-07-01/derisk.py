import sys
import time
from harness import ask, passage
from judge import STRICT

N = int(sys.argv[1]) if len(sys.argv) > 1 else 4

PROBES = [
    {"q": "According to the Asset Protection Zone requirements, how far from the dwelling must shrubs be located?", "expect": "twice the mature height"},
    {"q": "What is the maximum height that grasses are permitted to reach within the Inner Protection Area?", "expect": "10cm"},
    {"q": "To what height above ground must the lower limbs of all trees be removed?", "expect": "two metres"},
    {"q": "On Saturdays, what are the permitted working hours for construction or demolition?", "expect": "8.00am to 1.00pm"},
    {"q": "What contribution must be made to the Council's Biodiversity Offset Fund?", "expect": "$1,800.00"},
]

def with_retry(fn, *args, attempts=5):
    for i in range(attempts):
        try:
            return fn(*args)
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(2 ** i)

for probe in PROBES:
    print("=" * 80)
    print("Q:", probe["q"])
    print("expect:", probe["expect"])
    for _ in range(N):
        answer = with_retry(ask, STRICT, probe["q"], passage)
        one = " ".join(answer.split())
        refused = "NOT IN DOCUMENT" in answer.upper()
        has_expect = probe["expect"].lower() in answer.lower()
        print(f"  [refused={refused} has_expect={has_expect}] {one[:200]}")
    print()
