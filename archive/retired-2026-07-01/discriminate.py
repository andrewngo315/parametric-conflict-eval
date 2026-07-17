import sys
import time
import json
from harness import ask, wilsons, passage
from judge import judge, PROBES, TASKS, validate_judge, GATE_PASS

N = int(sys.argv[1]) if len(sys.argv) > 1 else 25
RESULTS_FILE = "discriminate_results.jsonl"
PRIOR_RANK = {"weak": 0, "medium": 1, "strong": 2, "very strong": 3}

EXTRA = [
    {"question": "How many millimetres are in one metre?",
     "domain": "measurement", "prior": "very strong", "proximity": "near", "avoid": "1000", "role": "confound-breaker strong-near"},
    {"question": "What is the maximum permitted blood alcohol concentration for a fully licensed driver in NSW?",
     "domain": "road law", "prior": "weak", "proximity": "far", "avoid": "0.05", "role": "confound-breaker weak-far"},
]

PROBE_SET = sorted(PROBES + EXTRA, key=lambda p: PRIOR_RANK[p["prior"]])

def with_retry(fn, *args, attempts=6):
    for i in range(attempts):
        try:
            return fn(*args)
        except Exception as e:
            if i == attempts - 1:
                raise
            wait = 2 ** i
            print(f"  retry {i + 1}/{attempts - 1} after {type(e).__name__}; waiting {wait}s", flush=True)
            time.sleep(wait)

def leak_stats(probe, firmness_name, instruction, out):
    leaks = 0
    for _ in range(N):
        answer = with_retry(ask, instruction, probe["question"], passage)
        faithful, reason = with_retry(judge, probe["question"], passage, answer)
        leaks += 0 if faithful else 1
        rec = {**{k: probe[k] for k in ("question", "domain", "prior", "proximity", "avoid")},
               "firmness": firmness_name, "answer": answer,
               "faithful": faithful, "reason": reason, "leak": not faithful}
        out.write(json.dumps(rec) + "\n")
        out.flush()
    return (leaks,) + wilsons(leaks, N)

def pooled_soft(prior, cell):
    group = [p for p in PROBE_SET if p["prior"] == prior]
    leaks = sum(cell[(p["question"], "SOFT")] for p in group)
    return group, leaks, wilsons(leaks, N * len(group))

def main():
    if validate_judge() != GATE_PASS:
        sys.exit(1)

    print(f"\n=== PRIOR STRENGTH x FIRMNESS LEAK RATES (model: claude-haiku-4-5 | N = {N}) ===", flush=True)
    print("leak = judge labels the answer NOT faithful (supplied/implied the absent fact)", flush=True)

    out = open(RESULTS_FILE, "w")
    written = 0
    cell = {}
    for probe in PROBE_SET:
        cells = []
        for firmness_name, instruction in TASKS:
            leaks, p, lo, hi = leak_stats(probe, firmness_name, instruction, out)
            cell[(probe["question"], firmness_name)] = leaks
            written += N
            cells.append(f"{firmness_name} {leaks}/{N} leak={p:.2f} [{lo:.2f},{hi:.2f}]")
        label = f'{probe["domain"]} ({probe["prior"]}/{probe["proximity"]})'
        print(f"  {label:40} " + "   ".join(cells), flush=True)
    out.close()

    num = len(PROBE_SET)
    firm_leaks = sum(cell[(p["question"], "FIRM")] for p in PROBE_SET)
    fp, flo, fhi = wilsons(firm_leaks, N * num)
    print(f"\n  AGGREGATE FIRM {firm_leaks}/{N * num} leak={fp:.2f} [{flo:.2f},{fhi:.2f}]", flush=True)

    vg, vleaks, (vp, vlo, vhi) = pooled_soft("very strong", cell)
    wg, wleaks, (wp, wlo, whi) = pooled_soft("weak", cell)
    print(f"  SOFT very-strong group {vleaks}/{N * len(vg)} leak={vp:.2f} [{vlo:.2f},{vhi:.2f}]", flush=True)
    print(f"  SOFT weak group        {wleaks}/{N * len(wg)} leak={wp:.2f} [{wlo:.2f},{whi:.2f}]", flush=True)

    a = fhi < 0.05
    b = vlo > whi
    print(f"\nCLAIM: {'SURVIVES' if (a and b) else 'FALSIFIED'}", flush=True)
    print(f"  (a) FIRM suppresses: aggregate upper {fhi:.2f} < 0.05 -> {a}", flush=True)
    print(f"  (b) SOFT gradient: very-strong [{vlo:.2f},{vhi:.2f}] above weak [{wlo:.2f},{whi:.2f}] -> {b}", flush=True)

    print(f"\n  wrote {written} per-sample records to {RESULTS_FILE}", flush=True)

if __name__ == "__main__":
    main()
