import json
def score_examples(examples):
    correct = 0
    for ex in examples:
        if ex["answer"] == ex["gold"]:
            correct = correct + 1
    total = len(examples)
    return correct / total

def precision_recall(examples):
    tp = 0
    fp = 0
    fn = 0
    for ex in examples:
        if ex["answer"] == "yes" and ex["gold"] == "yes":
            tp = tp + 1
        elif ex["answer"] == "yes" and ex["gold"] == "no":
            fp = fp + 1
        elif ex["answer"] == "no" and ex["gold"] == "yes":
            fn = fn + 1
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    f1 = 2 * (precision * recall) / (precision + recall)
    print("Precision:", round(precision, 2))
    print("Recall:", round(recall,2))
    print("F1:", round(f1, 2))


# test: 1 of 2 answers match, so the score must be 0.5
test_examples = [
    {"answer": "yes", "gold": "yes"},
    {"answer": "no", "gold": "yes"},
]
assert score_examples(test_examples) == 0.5
print("Test passed")
f = open("examples.json")
examples = json.load(f)
score = score_examples(examples)
print("Score:", round(score, 2))
precision_recall(examples)


