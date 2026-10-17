"""One-shot ledger-backed validation of frozen batches; never retries paid calls.

Only experiment model routing is changed in this process. The app configuration,
research and watch settings are untouched. All source inputs come from disk.
Usage: .venv/bin/python experiments/soclaas_replay/bounded_validation.py
       SOURCE_DIR OUTPUT_DIR MODEL --cap-usd 0.30 [--batches 6,8,14]
An existing output directory refuses another dispatch. Errors stop the run.
"""
import argparse
from contextlib import ExitStack
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from thesis.db import transaction  # noqa: E402
from thesis.providers import ledger, settings  # noqa: E402
from thesis.providers.anthropic_messages import SENTIMENT_WIRE  # noqa: E402
from thesis.research import sentiment  # noqa: E402
from experiments.soclaas_replay.phase1_offline import packet_from_request  # noqa: E402


def run(source, output, model, cap, batches=None):
    paths = sorted(source.glob("*.request.json"))
    if batches is not None:
        paths = [p for index,p in enumerate(paths) if index in batches]
    if not paths:
        raise ValueError("No frozen requests found")
    output.mkdir(parents=True,exist_ok=False)
    report=dict(model=model,tag=SENTIMENT_WIRE,planned=len(paths),calls=[],paid_usd="0",
                completed=False,app_research_writes=0)
    report_path=output/"validation.json"
    def save():
        report_path.write_text(json.dumps(report,indent=2)+"\n")
    save()
    with ExitStack() as stack:
        if model.startswith("claude-"):
            if model not in settings.ANTHROPIC_PRICES:
                raise ValueError("Experiment model has no recorded price")
            stack.enter_context(patch.object(settings,"PROVIDER","anthropic"))
            stack.enter_context(patch.object(settings,"MODEL",model))
            stack.enter_context(patch.object(settings,"REASONING_MODEL",model))
            stack.enter_context(patch.object(settings,"select",lambda _: ("anthropic",model,model)))
        elif model != settings.REASONING_MODEL:
            raise ValueError("Only the selected GPT model or a priced Claude model is allowed")
        for index,path in enumerate(paths):
            body=dict(json.loads(path.read_text()),model=model)
            packet=packet_from_request(body)
            maximum=Decimal(ledger.estimate(body))/ledger.NANO
            if Decimal(report["paid_usd"]) + maximum > cap:
                report["stopped"]="script_cap_before_dispatch"
                save()
                break
            key="experiment:bounded-validation:"+SENTIMENT_WIRE+":"+str(output.resolve())+":"+hashlib.sha256(ledger.canonical(body).encode()).hexdigest()
            # Refuse any preexisting identity, including unsettled attempts.
            with transaction() as conn:
                if conn.execute("SELECT 1 FROM model_calls WHERE request_key=%s",(key,)).fetchone():
                    raise ValueError("This experiment request was already attempted; no retry")
            (output/(path.stem+".request.json")).write_text(json.dumps(body,ensure_ascii=False))
            started=time.monotonic()
            try:
                call=ledger.execute(key,sentiment.PROMPT,body)
            except Exception as exc:
                report["stopped"]=type(exc).__name__
                with transaction() as conn:
                    attempt=conn.execute("SELECT id,status,error_code,reserved_nano_usd FROM model_calls WHERE request_key=%s",(key,)).fetchone()
                if attempt and attempt["status"] in {"dispatched","unresolved"}:
                    report["unresolved_maximum_usd"]=str(Decimal(attempt["reserved_nano_usd"])/ledger.NANO)
                    report["uncertain_call_id"]=str(attempt["id"])
                    report["failure_code"]=attempt["error_code"]
                save()
                print(json.dumps(dict(index=index,status="stopped",error=type(exc).__name__)),flush=True)
                break
            response=call["response_body"]
            (output/(path.stem+".response.json")).write_text(json.dumps(response,ensure_ascii=False,indent=2))
            charged=Decimal(call["charged_nano_usd"])/ledger.NANO
            report["paid_usd"]=str(Decimal(report["paid_usd"])+charged)
            row=dict(batch=index,input_file=path.name,call_id=str(call["id"]),seconds=round(time.monotonic()-started,2),
                     paid_usd=str(charged),structured=response.get("structured_output"),wire_format=response.get("wire_format"),
                     items=len(packet["sources"]))
            try:
                result=sentiment.render(call,packet)
            except ValueError as exc:
                row.update(passed=False,error=type(exc).__name__)
                report["calls"].append(row)
                report["stopped"]="validator_failure_no_retry"
                save()
                print(json.dumps(row),flush=True)
                break
            row.update(passed=True,repaired=result["repairs"]["repaired"])
            report["calls"].append(row)
            save()
            print(json.dumps(row),flush=True)
        report["completed"]=len(report["calls"])==len(paths) and all(c["passed"] for c in report["calls"])
        report["passed"]=sum(c["passed"] for c in report["calls"])
        report["items"]=sum(c["items"] for c in report["calls"])
        report["repaired"]=sum(c.get("repaired",0) for c in report["calls"])
        save()
    return report


if __name__ == "__main__":
    import os
    if os.environ.get("THESIS_TEST_OFFLINE") == "true":
        raise SystemExit("This live experiment cannot run in offline test mode")
    parser=argparse.ArgumentParser()
    parser.add_argument("source",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("model")
    parser.add_argument("--cap-usd",type=Decimal,required=True)
    parser.add_argument("--batches",type=lambda s:{int(i) for i in s.split(",")})
    args=parser.parse_args()
    result=run(args.source,args.output,args.model,args.cap_usd,args.batches)
    print(json.dumps({k:v for k,v in result.items() if k!="calls"}),flush=True)
