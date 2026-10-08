"""Explicit development evaluation using the original application ledger.

Default validates/estimates only. --execute dispatches ONE selected case. It
never changes product samples, private ideas, watches or alert publications.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from thesis import alert_quality
from thesis.config import DATA, ROOT
from thesis.db import transaction, one
from thesis.providers import ledger


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--manifest", type=Path, required=True)
    cli.add_argument("--case", required=True)
    cli.add_argument("--execute", action="store_true")
    args = cli.parse_args()
    manifest = json.loads(args.manifest.read_text())
    candidates = [alert_quality.Case.model_validate(c) for c in manifest["cases"]]
    if len({c.id for c in candidates}) != len(candidates):
        raise ValueError("Case IDs must be unique.")
    case = next((c for c in candidates if c.id == args.case), None)
    if not case:
        raise ValueError("Unknown frozen case.")
    module, body = alert_quality.request(case)
    maximum = ledger.estimate(body) / ledger.NANO
    print(
        case.id, "validated; maximum possible request charge USD", maximum, flush=True
    )
    if not args.execute:
        return
    # Same project's original private live-test area and actual restricted role.
    if not args.manifest.resolve().is_relative_to(DATA / "live-tests"):
        raise ValueError(
            "Live manifests must be stored in the original private evidence area."
        )
    if maximum > 0.25:
        raise ValueError(
            "This bounded evaluation allows at most USD0.25 reserved per case."
        )
    with transaction(manifest["owner"]) as conn:
        if not one(
            conn,
            "SELECT id FROM accounts WHERE id=%s AND label=%s",
            (manifest["owner"], "Phase 16 authored alert quality evaluation"),
        ):
            raise ValueError("Use the explicitly labelled evaluation account.")
    key = (
        "alert-eval:"
        + manifest["owner"]
        + ":"
        + alert_quality.digest(manifest)
        + ":"
        + case.id
    )
    out = args.manifest.parent / case.id
    out.mkdir(mode=0o700, exist_ok=True)
    before = ledger.snapshot()
    call = ledger.execute(
        key, "alert-quality:" + module.PROMPT, body, owner=manifest["owner"]
    )

    # Preserve raw evidence even if validation or scoring below rejects it.
    def write(name, value):
        p = out / name
        p.write_text(json.dumps(value, default=str, indent=2))
        p.chmod(0o600)

    write("call.json", call)
    result = module.render(call, case.packet)
    write("result.json", result)
    write("score.json", alert_quality.score(case, result))
    write(
        "run.json",
        dict(
            case=case.id,
            manifest_sha256=alert_quality.digest(manifest),
            request_sha256=case.request_sha256,
            before=before,
            after=ledger.snapshot(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        ),
    )
    print(
        case.id,
        "saved; criteria",
        alert_quality.score(case, result)["matched"],
        "/",
        alert_quality.score(case, result)["criteria"],
        flush=True,
    )


if __name__ == "__main__":
    main()
