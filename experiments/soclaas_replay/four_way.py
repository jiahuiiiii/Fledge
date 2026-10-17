"""Summary for the fair META run across every model tried (same requests)."""
import json, statistics, sys
from collections import Counter
from pathlib import Path

d = Path(sys.argv[1])
base = json.loads((d / "fair.json").read_text())
models = {"Opus 5.5": {}, "Sonnet 5.5": {}, "Haiku 5.5": {}, "GPT-5.5": {}, "GPT-5.4": {}, "GPT-5.4 mini": {}, "GPT-5.4 nano": {}, "DeepSeek V4.1 Flash": {}, "DeepSeek (OpenRouter)": {}}
for r in base:
    models["Opus 5.5"][r["batch"]] = (r["opus"], {i["label"]: i.get("opus") for i in r["items"]})
    models["DeepSeek V4.1 Flash"][r["batch"]] = (r["deepseek"], {i["label"]: i.get("deepseek") for i in r["items"]})
for name, f in (("Sonnet 5.5", "claude-sonnet-5-5"), ("Haiku 5.5", "claude-haiku-5-5"), ("GPT-5.5", "gpt-5.5-2026-04-23"),
                ("GPT-5.4", "gpt-5.4-2026-03-05"), ("GPT-5.4 mini", "gpt-5.4-mini-2026-03-17"), ("GPT-5.4 nano", "gpt-5.4-nano-2026-03-17"),
                ("DeepSeek (OpenRouter)", "openrouter-deepseek-v4.1-flash")):
    if not (d / f"fair-{f}.json").exists():
        models.pop(name); continue
    for r in json.loads((d / f"fair-{f}.json").read_text()):
        models[name][r["batch"]] = (r["result"], r["items"])
meta = {r["batch"]: {i["label"]: i for i in r["items"]} for r in base}

print(f"{'model':22s} pass  item-repair  median_s  max_s  out_tok  cost")
for name, runs in models.items():
    res = [runs[b][0] for b in sorted(runs)]
    ok = sum(not r.get("error") and not r["item_problems"] for r in res)
    bad = sum(len({p.split(':')[0] for p in r["item_problems"] if p.startswith("item_")}) for r in res)
    whole = sum(1 for r in res if r["item_problems"] and not any(p.startswith("item_") for p in r["item_problems"]))
    secs = [r["seconds"] for r in res if r.get("seconds")]
    toks = [r.get("output_tokens") or 0 for r in res if not r.get("error")]
    usd = sum(r.get("usd") or 0 for r in res)
    print(f"{name:22s} {ok:2d}/16  {16-whole:2d}/16 ({bad} items)  {statistics.median(secs):6.1f}  {max(secs):5.1f}  {statistics.median(toks):6.0f}  "
          + (f"US${usd:.3f}" if usd else "free (NUS)"))

print("\nAgreement with Opus (sources both labelled)")
fields = ("relevance", "sentiment", "kind", "impact")
for name in list(models)[1:]:
    pairs = [(models["Opus 5.5"][b][1].get(l), lab, meta[b][l]["channel"]) for b in models[name]
             for l, lab in models[name][b][1].items() if lab and models["Opus 5.5"][b][1].get(l)]
    out = []
    for f in fields:
        pool = [(a, c) for a, c, ch in pairs if f in ("relevance", "sentiment") or ch == "news"]
        out.append(f"{f} {100*sum(a[f]==c[f] for a,c in pool)/max(1,len(pool)):.0f}%")
    print(f"  {name:22s} n={len(pairs):3d}  " + "  ".join(out))

cases = [  # (batch, label, short text, my reading of the correct tone)
    (4, "item_195", "HN 'next level legal judo… still innovating… Terms of Service' (sarcasm)", "negative"),
    (3, "item_187", "HN '…almost none of them have' (cut off)", "unclear"),
    (8, "item_203", "HN '…still a bad look'", "negative"),
    (8, "item_200", "Reddit 'Meta Muse is cool, but I use Gemini more'", "mixed"),
    (8, "item_10", "Senators question Meta's $6.6B AI tax credits", "negative"),
    (6, "item_5", "'Meta climbed 12%: take profits or hold?' (question)", "neutral"),
]
print("\nProofread cases (tone; my reading in brackets)")
score = Counter()
for b, l, text, want in cases:
    row = []
    for name, runs in models.items():
        lab = runs.get(b, (None, {}))[1].get(l)
        got = lab["sentiment"] if lab else "—"
        score[name] += got == want
        row.append(f"{name.replace(' 5.5','').replace('DeepSeek V4.1 Flash','DS-NUS').replace('DeepSeek (OpenRouter)','DS-OR')}={got}")
    print(f"  [{want}] {text}\n      " + "  ".join(row))
print("  correct:", dict(score))

print("\nMarket-wide sell-off stories (relevance/tone)")
for b, labs in meta.items():
    for l, i in labs.items():
        t = i["title"]
        if any(k in t for k in ("Rotate Out Of AI", "AI Angst", "Magnificent Seven Stocks")):
            print(f"  {t[:80]!r}\n      " + "  ".join(
                f"{n.split()[0]}={(models[n][b][1].get(l) or {}).get('relevance')}/{(models[n][b][1].get(l) or {}).get('sentiment')}" for n in models))
for name, runs in models.items():
    labs = [x for b in runs for x in runs[b][1].values() if x]
    print(f"  {name:22s} tone {dict(Counter(x['sentiment'] for x in labs))}")
