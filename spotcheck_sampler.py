import hashlib
import json
import random
import sys
from harness import FACT_BY_NAME, CAVEAT_RESULTS, ABSTENTION_RESULTS, ABSENCE_RESULTS

CAVEAT_GOLD = "data/caveat_gold.json"
ABSTENTION_GOLD = "data/abstention_gold.json"
COUNTS = {"cv": 30, "ab": 18, "ma": 12}
STANCE_CAPS = [("endorsed", 8), ("questioned", 10), ("declined", 4)]
UNGROUNDED_CAPS = {"ab": 6, "ma": 4}
PROBE_RESULTS = "data/opus_fi_probe.jsonl"
PROBE_COUNT = 30
PROBE_STANCE_CAPS = [("endorsed", 16), ("questioned", 8), ("declined", 2)]
ADOPTION_ROWS = "data/adoption_v2.jsonl"
ADOPTION_GOLD = "data/adoption_gold.json"
ADOPTION_COUNT = 30
ADOPTION_CAPS = [("silent_override", 6), ("true_only_rest", 2), ("neither_pert", 7), ("neither_s0", 3), ("both", 6)]


def load_results(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def coverage_pick(pool, k, keys, rng):
    pool = pool[:]
    rng.shuffle(pool)
    picked = []
    seen = {key: set() for key in keys}
    while pool and len(picked) < k:
        best = max(pool, key=lambda r: sum(r[key] not in seen[key] for key in keys))
        pool.remove(best)
        picked.append(best)
        for key in keys:
            seen[key].add(best[key])
    return picked


def sample_caveat(rows, n, rng):
    keys = ["instruction", "severity", "document"]
    picked = []
    for stance, cap in STANCE_CAPS:
        picked += coverage_pick([r for r in rows if r["stance"] == stance], cap, keys, rng)
    picked += coverage_pick([r for r in rows if r["stance"] == "silent"], n - len(picked), keys, rng)
    return picked[:n]


def sample_binary(rows, n, ungrounded_cap, keys, rng):
    picked = coverage_pick([r for r in rows if r["label"] == "ungrounded"], ungrounded_cap, keys, rng)
    picked += coverage_pick([r for r in rows if r["label"] == "faithful"], n - len(picked), keys, rng)
    return picked[:n]


def caveat_gold_row(r, role):
    fact = FACT_BY_NAME[r["fact"]]
    step = next(s for s in fact["steps"] if s["severity"] == r["severity"])
    return {"q": fact["q"], "replace": [list(pair) for pair in step["replace"]],
            "target_string": r["target_string"], "severity": r["severity"], "document": r["document"],
            "role": role, "instruction": r["instruction"], "candidate": r["model"],
            "human": "", "human_corroboration": "", "answer": r["answer"]}


def abstention_gold_row(r, role):
    return {"item_id": r["item_id"], "doc": r["document"], "prior_strength": r["prior_strength"],
            "proximity": r["proximity"], "domain": r["domain"], "parametric_answer": r["parametric_answer"],
            "q": r["q"], "role": role, "instruction": r["instruction"], "candidate": r["model"],
            "human": "", "answer": r["answer"]}


def absence_gold_row(r, role):
    return {"item_id": "absent " + r["fact"], "doc": r["document"], "fact": r["fact"],
            "evidence_state": r["evidence_state"], "prior_strength": None, "proximity": "matched",
            "domain": "matched-absence", "parametric_answer": r["true"], "q": r["q"], "role": role,
            "instruction": r["instruction"], "candidate": r["model"], "human": "", "answer": r["answer"]}


def sidecar_entry(kind, r, role):
    if kind == "cv":
        return {"role": role, "stance": r["stance"], "corroboration": r["corroboration"], "label": r["label"]}
    return {"role": role, "label": r["label"], "verbatim_abstention": r["verbatim_abstention"]}


def sidecar_path(tag, seed):
    return f"data/spotcheck_sidecar_{tag}_{seed}.json"


def role_prefix(tag, seed):
    return f"{tag}-spotcheck seed{seed} "


def sample_probe_caveat(rows, n, rng):
    keys = ["severity", "document"]
    picked = []
    for stance, cap in PROBE_STANCE_CAPS:
        picked += coverage_pick([r for r in rows if r["stance"] == stance], cap, keys, rng)
    picked += coverage_pick([r for r in rows if r["stance"] == "silent"], n - len(picked), keys, rng)
    return picked[:n]


def draw_probe(tag, seed):
    rng = random.Random(seed)
    sample = sample_probe_caveat(load_results(PROBE_RESULTS), PROBE_COUNT, rng)
    gold = {"cv": [], "ab": [], "ma": []}
    sidecar = []
    for i, r in enumerate(sample):
        role = f"{role_prefix(tag, seed)}cv{i:02d}"
        gold["cv"].append(caveat_gold_row(r, role))
        sidecar.append(sidecar_entry("cv", r, role))
    return gold, sidecar


def load_adoption_joined():
    idx = {}
    for r in load_results(CAVEAT_RESULTS) + load_results(PROBE_RESULTS):
        if r.get("truncated"):
            continue
        k = (r["model"], r["instruction"], r["fact"], r["severity"], r.get("rep"), r.get("run_id"),
             hashlib.sha1(r["answer"].encode()).hexdigest()[:12])
        idx.setdefault(k, r)
    rows = []
    for a in load_results(ADOPTION_ROWS):
        r = idx.get((a["model"], a["instruction"], a["fact"], a["severity"], a.get("rep"),
                     a.get("run_id"), a["answer_sha1"]))
        if r:
            rows.append({**a, "answer": r["answer"], "target_string": r["target_string"],
                         "true": r["true"], "q": FACT_BY_NAME[a["fact"]]["q"]})
    return rows


def sample_adoption(rows, n, rng):
    keys = ["model", "instruction", "fact"]
    pools = {
        "silent_override": [a for a in rows if a["silent_override"]],
        "true_only_rest": [a for a in rows if a["adoption"] == "true_only" and not a["silent_override"]],
        "neither_pert": [a for a in rows if a["adoption"] == "neither" and a["severity"] >= 1
                         and a["stance"] != "declined"],
        "neither_s0": [a for a in rows if a["adoption"] == "neither" and a["severity"] == 0
                       and a["stance"] not in ("questioned", "declined")],
        "both": [a for a in rows if a["adoption"] == "both"],
    }
    picked = []
    for bucket, cap in ADOPTION_CAPS:
        picked += coverage_pick(pools[bucket], cap, keys, rng)
    picked += coverage_pick([a for a in rows if a["adoption"] == "target_only"], n - len(picked), keys, rng)
    return picked[:n]


def adoption_gold_row(a, role):
    return {"q": a["q"], "target_string": a["target_string"], "true": a["true"],
            "severity": a["severity"], "document": a["document"], "role": role,
            "instruction": a["instruction"], "candidate": a["model"], "human": "", "answer": a["answer"]}


def adoption_sidecar_entry(a, role):
    return {"role": role, "adoption": a["adoption"], "reports_target": a["reports_target"],
            "reports_true": a["reports_true"], "silent_override": a["silent_override"],
            "candidate_stance": a["stance"], "prior_known_any": a["prior_known_any"]}


def draw_adoption(tag, seed):
    rng = random.Random(seed)
    sample = sample_adoption(load_adoption_joined(), ADOPTION_COUNT, rng)
    gold, sidecar = [], []
    for i, a in enumerate(sample):
        role = f"{role_prefix(tag, seed)}ad{i:02d}"
        gold.append(adoption_gold_row(a, role))
        sidecar.append(adoption_sidecar_entry(a, role))
    return gold, sidecar


def merge_adoption(gold, sidecar, tag, seed):
    prefix = role_prefix(tag, seed)
    try:
        existing = json.load(open(ADOPTION_GOLD))
    except FileNotFoundError:
        existing = []
    clashes = [g["role"] for g in existing if str(g.get("role", "")).startswith(prefix)]
    if clashes:
        raise SystemExit(f"{ADOPTION_GOLD} already contains {len(clashes)} rows for {prefix!r} -- refusing to merge twice")
    with open(ADOPTION_GOLD, "w") as f:
        json.dump(existing + gold, f, indent=2)
    print(f"{ADOPTION_GOLD}: +{len(gold)} unlabeled rows (total {len(existing) + len(gold)}) -- "
          f"label human with one of: target_only | both | true_only | neither")
    with open(sidecar_path(tag, seed), "w") as f:
        json.dump(sidecar, f, indent=2)
    print(f"{sidecar_path(tag, seed)}: classifier verdicts held out here -- do not open until labelling is done")


def draw(model, tag, seed):
    rng = random.Random(seed)
    samples = {
        "cv": sample_caveat([r for r in load_results(CAVEAT_RESULTS) if r["model"] == model], COUNTS["cv"], rng),
        "ab": sample_binary([r for r in load_results(ABSTENTION_RESULTS) if r["model"] == model],
                            COUNTS["ab"], UNGROUNDED_CAPS["ab"], ["instruction", "item_id"], rng),
        "ma": sample_binary([r for r in load_results(ABSENCE_RESULTS) if r["model"] == model],
                            COUNTS["ma"], UNGROUNDED_CAPS["ma"], ["instruction", "fact"], rng),
    }
    builders = {"cv": caveat_gold_row, "ab": abstention_gold_row, "ma": absence_gold_row}
    gold = {"cv": [], "ab": [], "ma": []}
    sidecar = []
    for kind, rows in samples.items():
        for i, r in enumerate(rows):
            role = f"{role_prefix(tag, seed)}{kind}{i:02d}"
            gold[kind].append(builders[kind](r, role))
            sidecar.append(sidecar_entry(kind, r, role))
    return gold, sidecar


def summarize(gold):
    for kind, rows in gold.items():
        by_instruction = {}
        for r in rows:
            by_instruction[r["instruction"]] = by_instruction.get(r["instruction"], 0) + 1
        print(f"{kind}: {len(rows)} rows  {by_instruction}")
        if kind == "cv":
            by_severity = {}
            for r in rows:
                by_severity[r["severity"]] = by_severity.get(r["severity"], 0) + 1
            print(f"    severities: {dict(sorted(by_severity.items()))}")


def merge(gold, sidecar, tag, seed):
    prefix = role_prefix(tag, seed)
    for path, new_rows in [(CAVEAT_GOLD, gold["cv"]), (ABSTENTION_GOLD, gold["ab"] + gold["ma"])]:
        existing = json.load(open(path))
        clashes = [g["role"] for g in existing if str(g.get("role", "")).startswith(prefix)]
        if clashes:
            raise SystemExit(f"{path} already contains {len(clashes)} rows for {prefix!r} -- refusing to merge twice")
        with open(path, "w") as f:
            json.dump(existing + new_rows, f, indent=2)
        print(f"{path}: +{len(new_rows)} unlabeled rows (total {len(existing) + len(new_rows)})")
    with open(sidecar_path(tag, seed), "w") as f:
        json.dump(sidecar, f, indent=2)
    print(f"{sidecar_path(tag, seed)}: judge verdicts held out here -- do not open until labelling is done")


def compare(tag, seed):
    verdicts = {e["role"]: e for e in json.load(open(sidecar_path(tag, seed)))}
    prefix = role_prefix(tag, seed)
    rows = []
    for path in (CAVEAT_GOLD, ABSTENTION_GOLD, ADOPTION_GOLD):
        try:
            rows += [g for g in json.load(open(path)) if str(g.get("role", "")).startswith(prefix)]
        except FileNotFoundError:
            pass
    if len(rows) != len(verdicts):
        print(f"WARNING: {len(rows)} gold rows vs {len(verdicts)} sidecar entries")
    agree = 0
    misses = []
    for g in rows:
        v = verdicts[g["role"]]
        judge_call = v.get("adoption") or (v["stance"] if "stance" in v else v["label"])
        if not g["human"]:
            misses.append((g["role"], "UNLABELLED", judge_call))
            continue
        if g["human"] == judge_call:
            agree += 1
        else:
            misses.append((g["role"], g["human"], judge_call))
    print(f"stance/label agreement: {agree}/{len(rows)}")
    for role, human, judge_call in misses:
        print(f"  {role}: human={human} judge={judge_call}")
    corro = [(g, verdicts[g["role"]]) for g in rows
             if "human_corroboration" in g and g.get("human_corroboration", "") != ""]
    if corro:
        c_agree = sum(g["human_corroboration"] == v["corroboration"] for g, v in corro)
        print(f"corroboration agreement: {c_agree}/{len(corro)}")
        for g, v in corro:
            if g["human_corroboration"] != v["corroboration"]:
                print(f"  {g['role']}: human={g['human_corroboration']} judge={v['corroboration']}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 4 and args[0] == "sample":
        model, tag, seed = args[1], args[2], int(args[3])
        gold, sidecar = draw(model, tag, seed)
        summarize(gold)
        if "--merge" in args:
            merge(gold, sidecar, tag, seed)
        else:
            print("\n  (dry run -- add --merge to append unlabeled rows to the gold files and write the sidecar)")
    elif len(args) >= 3 and args[0] == "probe":
        tag, seed = args[1], int(args[2])
        gold, sidecar = draw_probe(tag, seed)
        summarize(gold)
        if "--merge" in args:
            merge(gold, sidecar, tag, seed)
        else:
            print("\n  (dry run -- add --merge to append unlabeled rows to the gold files and write the sidecar)")
    elif len(args) >= 3 and args[0] == "adoption":
        tag, seed = args[1], int(args[2])
        gold, sidecar = draw_adoption(tag, seed)
        by_outcome = {}
        for e in sidecar:
            by_outcome[e["adoption"]] = by_outcome.get(e["adoption"], 0) + 1
        print(f"adoption: {len(gold)} rows  {by_outcome}  silent_override: {sum(e['silent_override'] for e in sidecar)}")
        if "--merge" in args:
            merge_adoption(gold, sidecar, tag, seed)
        else:
            print("\n  (dry run -- add --merge to append unlabeled rows to the gold file and write the sidecar)")
    elif len(args) == 3 and args[0] == "compare":
        compare(args[1], int(args[2]))
    else:
        print("usage: python3 spotcheck_sampler.py sample <model> <tag> <seed> [--merge] | probe <tag> <seed> [--merge] | adoption <tag> <seed> [--merge] | compare <tag> <seed>")
        sys.exit(1)
