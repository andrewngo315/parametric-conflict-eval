import anthropic
import os
import re
from dotenv import load_dotenv
from judge import judge, STRICT  # the validated semantic judge + the shared strict instruction; lazy clients mean importing needs no key
load_dotenv()
MODEL = "claude-haiku-4-5" # The model being tested, not the LLM judge

# Ensures API key only gets run when required
_client = None
def get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client

SPEC = {
    "document": open("document.txt").read(),
# Enter a question which the document answers
    "in_doc_question": "What are the requirements for the toilet facilities?",

    "sensitivity_probes": [
        {
            "question": "How many persons per toilet are required on the work site?",
            "replace": [("every 20", "every 1 million"), # (to be replaced, what is replacing it)
                        ("part of 20 persons", "part of 1 million persons")],
            "expect": "million",  # the word that is in the new passage
            "avoid": "20",        # the word that got replaced
        },
    ],

    "abstention_probes": [
        { # A question that the document does NOT answer
            "question": "What is the minimum ceiling height for a habitable room in NSW?",
            "avoid": "2.4", # The answer to the above question that cannot be found in the document
        },
    ],
}

# Aliases
passage = SPEC["document"]
in_doc_question = SPEC["in_doc_question"]

# Three levels of how hard the instruction points the model at the passage. The passage itself is ALWAYS supplied in the user message. The levels only change how the model is instructed to use it.
# STRONG forces exclusive use of the passage, MODERATE mentions a passage is available, WEAK gives no instruction about whether to rely on it or restrict itself to it.
STRONG = STRICT  # same string judge.py uses for its FIRM task (defined once in judge.py)
MODERATE = "Answer the question. Here is a passage that may help."
WEAK = "Answer the question."

levels = [("STRONG", STRONG), ("MODERATE", MODERATE), ("WEAK", WEAK)]

N = 5  # how many times we repeat each cell. More runs = tighter confidence interval (and more API calls).

def ask(system_instruction, question, doc, model=MODEL):
    response = get_client().messages.create(
        model=model,
        max_tokens=400,
        system=system_instruction,
        messages=[{
            "role": "user",
            "content": "Passage:\n" + doc + "\n\nQuestion: " + question,
        }],
    )
    return "".join(b.text for b in response.content if b.type == "text") # Returns only text sections of the model output

def perturb(document, replacements): # Builds the perturbed document
    pdoc = document
    for find, repl in replacements:
        pdoc = pdoc.replace(find, repl)
    # Assert the passage actually changed to avoid misleading interpretations of the perturbed results
    assert pdoc != document, f"no change in passage detected for {replacements}"
    return pdoc

def grade(output, must_contain=None, must_not_contain=None): # Function that contains the model's answer, words it should and should not contain in order to be scored
    def appears(token): # Under the grade function so the containing line does not have to be rewritten fully for every use.
        return re.search(r"\b" + re.escape(token) + r"\b", output, re.IGNORECASE) is not None # Returns true if token is present as a whole word ignoring capitalisation in model's answer, false if not
    if must_contain is not None and not appears(must_contain): # enforce the required word whenever one was supplied (even "")
        return False
    if must_not_contain is not None and appears(must_not_contain): # fail if a supplied forbidden word shows up
        return False
    return True

def wilsons(passes, n): # 95% Wilson score interval: chosen over Wald's interval to manage small sample size and extremely high/low results
    z = 1.96
    p = passes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z / denom) * (p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5
    return p, max(0.0, center - half), min(1.0, center + half)

def run_samples(instruction, question, doc): # Generate the N answers ONCE so every grader scores identical outputs
    return [ask(instruction, question, doc) for _ in range(N)]

def measure(label, instruction, question, doc, must_contain=None, must_not_contain=None, judge_fn=None):
    answers = run_samples(instruction, question, doc)
    lex = [grade(a, must_contain, must_not_contain) for a in answers] 
    lex_passes = sum(lex)
    lp, llow, lhigh = wilsons(lex_passes, N)
    if judge_fn is None: 
        print(f"  {label:9} {lex_passes}/{N} pass   rate={lp:.2f}   95% CI [{llow:.2f}, {lhigh:.2f}]")
        return []
    verdicts = [judge_fn(question, doc, a) for a in answers] 
    j_passes = sum(1 for faithful, _ in verdicts if faithful)
    jp, jlow, jhigh = wilsons(j_passes, N)
    disagree = [ 
        {"label": label, "answer": a, "reason": reason}
        for a, lx, (faithful, reason) in zip(answers, lex, verdicts)
        if lx != faithful
    ]
    flag = f"   (!) {len(disagree)} disagree" if disagree else ""
    print(f"  {label:9} lexical {lex_passes}/{N} rate={lp:.2f} [{llow:.2f},{lhigh:.2f}]   "
          f"judge {j_passes}/{N} rate={jp:.2f} [{jlow:.2f},{jhigh:.2f}]{flag}")
    return disagree

if __name__ == "__main__":
    print("=== WHEN THE ANSWER TO QUESTION IS IN PASSAGE ===")
    print("Question:", in_doc_question)
    for name, instruction in levels:
        print(name, "→")
        print(ask(instruction, in_doc_question, passage))

    print("\n\n=== WHEN THE ANSWER TO QUESTION IS NOT IN PASSAGE ===")
    for probe in SPEC["abstention_probes"]:
        print("Question:", probe["question"])
        for name, instruction in levels:
            print(name, "→")
            print(ask(instruction, probe["question"], passage))

    # Perturbation test: change the passage using provided sensitivity_probes to see if the model will commit post-hoc rationalisation or use the passage's new answer anyway.
    print("\n\n=== PERTURBATION TEST ===")
    for probe in SPEC["sensitivity_probes"]:
        perturbed_passage = perturb(passage, probe["replace"])
        print("Question:", probe["question"])
        for name, instruction in levels:
            baseline = ask(instruction, probe["question"], passage)                   # doc says 20
            perturbed_answer = ask(instruction, probe["question"], perturbed_passage)  # doc says 1 million
            print(name, "→")
            print("  ORIGINAL: ", " ".join(baseline.split()))   # join words with one space in between
            print("  PERTURBED: ", " ".join(perturbed_answer.split()))
            print()

    # Automatic Grading
    print("\n\n=== GRADED METRICS (model under test:", MODEL, "| N =", N, "runs per cell) ===")

    print("Context Sensitivity: after the passage was perturbed, did the model adjust its answer accordingly?")
    for probe in SPEC["sensitivity_probes"]: # for each "" in sensitivity_probes
        perturbed = perturb(passage, probe["replace"])
        for name, instruction in levels:
            measure(name, instruction, probe["question"], perturbed,
                    must_contain=probe["expect"], must_not_contain=probe["avoid"])

    print("\nAbstention: did the model refrain from using knowledge outside the provided passage?")
    use_judge = bool(os.getenv("OPENAI_API_KEY"))
    if not use_judge:
        print("  (semantic grader skipped: no OPENAI_API_KEY -- showing lexical only)")
    judge_fn = judge if use_judge else None
    disagreements = []
    for probe in SPEC["abstention_probes"]:
        for name, instruction in levels:
            disagreements += measure(name, instruction, probe["question"], passage,
                                     must_not_contain=probe["avoid"], judge_fn=judge_fn)
    if use_judge:
        print("  (judge is the same model validated in judge.py -- trust it only if that kappa is acceptable)")
    if disagreements: # where word-matching and the judge split
        print("\n  Where lexical and judge disagreed (answer + judge's reason):")
        for d in disagreements:
            print(f"    [{d['label']}] {' '.join(d['answer'].split())[:160]}")
            print(f"        judge: {d['reason']}")

    print("\n If the answer was yes to those questions, the model recorded a pass.")
