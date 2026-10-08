"""Explicit, budgeted authored-evidence check. Never invoked by the test suite."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from .config import ROOT, INSTRUMENT, OWNER
from .fixtures import RELEASES, STAGES, uid, dt
from .research.pipeline import normalize_article
from .research.briefs import source_packet, select_passages
from .providers.ledger import snapshot


def packet_for(stage):
    documents = []
    for number, entry in RELEASES.items():
        if number > stage:
            continue
        stamp = dt(STAGES[number]["as_of"])
        article = normalize_article(
            dict(
                id=uid(f"article-{number}"),
                headline=entry["title"],
                summary=entry["body"],
                source_name=entry["source"],
                source_type="recorded",
                url=f"fixture://northstar/{entry['key']}",
                published_at=stamp,
                fetched_at=stamp,
            )
        )
        documents.append(
            dict(
                id=uid(f"document-{number}"),
                document_id=uid(entry["key"]),
                instrument_id=INSTRUMENT,
                entitlement="fictional",
                headline=article.headline,
                body=article.summary,
                source_name=(
                    "Northstar company release"
                    if entry["source"] == "company"
                    else "Sample Industry Wire"
                ),
                published_at=stamp,
                available_at=stamp,
                content_hash=article.content_hash,
                supersedes_id=uid("document-2") if number == 4 else None,
            )
        )
    documents.sort(key=lambda d: (d["available_at"], d["id"]))
    return source_packet(documents, INSTRUMENT, STAGES[stage]["as_of"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", choices=["baseline", "contrary", "restatement"], default="baseline"
    )
    args = parser.parse_args()
    stage = {"baseline": 0, "contrary": 2, "restatement": 4}[args.case]
    packet = packet_for(stage)
    before = snapshot()
    result = select_passages(packet)
    after = snapshot()
    # Same-request replay must not perform another dispatch or add a charge.
    again = select_passages(packet)
    assert again == result and snapshot() == after
    chosen = {p["document_id"] for p in result["passages"]}
    required = {
        uid("document-" + str(n))
        for n in ([0] if stage == 0 else [1, 2] if stage == 2 else [1, 4])
    }
    passed = required.issubset(chosen) and (
        stage != 4 or uid("document-2") not in chosen
    )
    record = dict(
        case=args.case,
        at=datetime.now(timezone.utc).isoformat(),
        passed=passed,
        required_source_ids=sorted(required),
        chosen_source_ids=sorted(chosen),
        replay_without_new_charge=True,
        before=before,
        after=after,
        result=result,
    )
    folder = ROOT / ".local" / "live-tests"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / (args.case + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + result["call_id"] + ".json")
    path.write_text(json.dumps(record, indent=2))
    path.chmod(0o600)
    print(
        json.dumps(
            dict(case=args.case, passed=passed, spending=after, record=str(path))
        )
    )
    if not passed:
        raise SystemExit(
            "Selection did not meet the authored coverage expectation; inspect saved result"
        )


if __name__ == "__main__":
    main()
