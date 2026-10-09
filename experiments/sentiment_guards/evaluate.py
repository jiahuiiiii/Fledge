"""Offline confusion tables. This module cannot dispatch a provider request."""
import argparse
import json
from collections import Counter
from pathlib import Path
from thesis.research import sentiment, sentiment_guards

LABELS = ("positive", "negative", "mixed", "neutral", "unclear")
DATASET = Path(__file__).with_name("broadcom-social-50.json")


def score(records, predictions):
    confusion = {label: {other: 0 for other in LABELS} for label in LABELS}
    missing, disagreements = [], []
    for r in records:
        key = r["source"]["id"]
        if key not in predictions:
            missing.append(key)
            continue
        actual, expected = predictions[key], r["expected_sentiment"]
        if actual not in LABELS:
            raise ValueError("Unknown prediction label")
        confusion[expected][actual] += 1
        if actual != expected:
            disagreements.append(dict(source_id=key, item=r["source"]["label"], expected=expected, observed=actual, requires_owner_review=r["requires_owner_review"]))
    return dict(compared=len(records)-len(missing), matches_developer_reference=sum(confusion[k][k] for k in LABELS),
                missing=missing, confusion_expected_rows_observed_columns=confusion, disagreements=disagreements)


def replay(dataset):
    records = dataset["records"]
    raw, checked, changes = {}, {}, []
    for r in records:
        original = r["model_item"]
        item = sentiment.Item.model_validate({k: original[k] for k in sentiment.Item.model_fields if k in original})
        result = sentiment_guards.apply(item, r["source"], dataset["company"])
        key = r["source"]["id"]
        raw[key] = item.sentiment
        checked[key] = result.get("sentiment", item.sentiment)
        if raw[key] != checked[key]:
            changes.append(dict(item=r["source"]["label"], source_id=key, before=raw[key], after=checked[key], rule=result["guard"]["rule"]))
    return dict(reference=dataset["provenance"], method="Offline guards applied to original v22 outputs; v23 was not dispatched.",
                original=score(records,raw), checked=score(records,checked), changes=changes)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, help="An already-generated analysis JSON. No model request is made.")
    args=parser.parse_args()
    dataset=json.loads(DATASET.read_text())
    if args.predictions:
        value=json.loads(args.predictions.read_text())
        value=value.get("result",value)
        result=score(dataset["records"],{i["source_id"]:i["sentiment"] for i in value["items"]})
    else:
        result=replay(dataset)
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
