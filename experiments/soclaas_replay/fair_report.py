"""Summarise fair.json from fair_compare.py."""
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

rows = json.loads(Path(sys.argv[1]).read_text())
models = ("opus", "deepseek")


def passed(r, m):
    return not r[m].get("error") and r[m].get("problem") is None


print(f"batches: {len(rows)}, sources: {sum(r['sources'] for r in rows)}")
for m in models:
    ok = sum(passed(r, m) for r in rows)
    secs = [r[m]["seconds"] for r in rows if r[m].get("seconds")]
    out = [r[m].get("output_tokens") or 0 for r in rows if not r[m].get("error")]
    # Item-level repair: keep every item without its own problem, drop the rest.
    bad_items = sum(len({p.split(":")[0] for p in r[m]["item_problems"] if p.startswith("item_")}) for r in rows)
    whole = sum(1 for r in rows if r[m]["item_problems"] and not any(p.startswith("item_") for p in r[m]["item_problems"]))
    usd = sum(r[m].get("usd") or 0 for r in rows)
    print(f"\n{m}: {ok}/{len(rows)} batches pass the app validator | time median {statistics.median(secs):.1f}s max {max(secs):.1f}s"
          f" | output tokens median {statistics.median(out):.0f}" + (f" | cost US${usd:.3f}" if usd else ""))
    print(f"   with item-level repair: {bad_items} bad items dropped, {whole} batches still unusable as a whole")
    for r in rows:
        if not passed(r, m):
            print(f"   batch {r['batch']:2d} failed: {r[m].get('error') or r[m].get('problem')}")

items = [i for r in rows for i in r["items"] if "opus" in i and "deepseek" in i]
news = [i for i in items if i["channel"] == "news"]
print(f"\nsources labelled by both: {len(items)} ({len(news)} news, {len(items) - len(news)} social)")
for f in ("relevance", "sentiment", "basis", "statement", "kind", "impact"):
    pool = news if f in ("kind", "impact") else items
    same = sum(i["opus"][f] == i["deepseek"][f] for i in pool)
    print(f"  {f:10s} agree {same}/{len(pool)} ({100 * same / max(1, len(pool)):.0f}%)")
alert = lambda x: x["kind"] in ("reported_event", "unconfirmed_event") and x["impact"] in ("adverse", "mixed")
print(f"  adverse-news alert candidates: Opus {sum(alert(i['opus']) for i in news)}, DeepSeek {sum(alert(i['deepseek']) for i in news)},"
      f" both {sum(alert(i['opus']) and alert(i['deepseek']) for i in news)}")
for m in models:
    print(f"  {m:8s} tone {dict(Counter(i[m]['sentiment'] for i in items))} | relevance {dict(Counter(i[m]['relevance'] for i in items))}")
print("\nDISAGREEMENTS on relevance / sentiment / event kind / impact")
for i in items:
    if any(i["opus"][f] != i["deepseek"][f] for f in ("relevance", "sentiment", "kind", "impact")):
        fmt = lambda x: "/".join(str(x[f]) for f in ("relevance", "sentiment", "kind", "impact"))
        print(f"- [{i['channel']}{'/' + i['platform'] if i.get('platform') else ''}] {i['label']} {i['title'][:100]!r}\n"
              f"    Opus     {fmt(i['opus'])}\n    DeepSeek {fmt(i['deepseek'])}")
