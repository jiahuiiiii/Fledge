"""Summarise comparison.json from replay.py: agreement, timing and every disagreement."""
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

rows = json.loads(Path(sys.argv[1]).read_text())
fields = ("relevance", "sentiment", "basis", "statement", "kind", "impact")
valid = [r for r in rows if not r["soclaas_problems"] and not r["claude_problems"]]
print(f"batches: {len(rows)} sent, {len(valid)} with both answers passing the app checks")
for r in rows:
    if r["soclaas_problems"]:
        print("  SOC LaaS failed", r["call_id"][:8], "-", "; ".join(r["soclaas_problems"])[:300])
    if r["claude_problems"]:
        print("  Claude failed  ", r["call_id"][:8], "-", "; ".join(r["claude_problems"])[:300])

secs = [r["soclaas"].get("seconds") for r in rows if r["soclaas"].get("seconds")]
csecs = [r["claude_seconds"] for r in rows]
reason = [((r["soclaas"].get("usage") or {}).get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
          for r in rows if r["soclaas"].get("usage")]
out = [(r["soclaas"].get("usage") or {}).get("completion_tokens", 0) for r in rows if r["soclaas"].get("usage")]
print(f"time per batch  SOC LaaS median {statistics.median(secs):.1f}s max {max(secs):.1f}s | "
      f"Claude median {statistics.median(csecs):.1f}s max {max(csecs):.1f}s")
print(f"SOC LaaS output tokens median {statistics.median(out):.0f} (reasoning {statistics.median(reason):.0f}); "
      f"Claude output tokens median {statistics.median([r['claude_output_tokens'] for r in rows]):.0f}")
print(f"coverage links: Claude {sum(r['claude_links'] for r in valid)}, SOC LaaS {sum(r['soclaas_links'] for r in valid)}")

items = [i for r in valid for i in r["items"]]
news = [i for i in items if i["channel"] == "news"]
print(f"\nsources compared: {len(items)} ({len(news)} news, {len(items) - len(news)} social)")
for f in fields:
    pool = news if f in ("kind", "impact") else items
    same = sum(i["claude"][f] == i["soclaas"][f] for i in pool)
    print(f"  {f:10s} agree {same}/{len(pool)} ({100 * same / max(1, len(pool)):.0f}%)")
rel = [i for i in items if i["claude"]["relevance"] == "relevant" and i["soclaas"]["relevance"] == "relevant"]
same = sum(i["claude"]["sentiment"] == i["soclaas"]["sentiment"] for i in rel)
print(f"  sentiment where both say relevant: {same}/{len(rel)}")
alert = lambda x: x["kind"] in ("reported_event", "unconfirmed_event") and x["impact"] in ("adverse", "mixed")
print(f"  would trigger an adverse-news alert: Claude {sum(alert(i['claude']) for i in news)}, "
      f"SOC LaaS {sum(alert(i['soclaas']) for i in news)}, both {sum(alert(i['claude']) and alert(i['soclaas']) for i in news)}")
print("  label totals Claude  ", dict(Counter(i["claude"]["sentiment"] for i in items)))
print("  label totals SOC LaaS", dict(Counter(i["soclaas"]["sentiment"] for i in items)))
print("  relevance Claude  ", dict(Counter(i["claude"]["relevance"] for i in items)))
print("  relevance SOC LaaS", dict(Counter(i["soclaas"]["relevance"] for i in items)))

print("\nDISAGREEMENTS (relevance / sentiment / event kind / impact)")
for i in items:
    diff = [f for f in ("relevance", "sentiment", "kind", "impact") if i["claude"][f] != i["soclaas"][f]]
    if diff:
        c = "/".join(str(i["claude"][f]) for f in ("relevance", "sentiment", "kind", "impact"))
        s = "/".join(str(i["soclaas"][f]) for f in ("relevance", "sentiment", "kind", "impact"))
        print(f"- [{i['channel']}{'/' + i['platform'] if i.get('platform') else ''}] {i['label']} {i['title'][:100]!r}\n"
              f"    Claude {c}\n    SOC    {s}")
