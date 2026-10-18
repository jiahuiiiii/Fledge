"""Estimate by default; execute one approved, capped frozen explainer trial.

Never changes .env, watches, saved research or publications. Paid traffic goes
through the existing ledger, sequentially, stopping on the first failure without
retry. Process-only role selection ends with the command, not the running app.
"""
import argparse
from contextlib import ExitStack
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from thesis.db import transaction,one  # noqa: E402
from thesis.providers import ledger,settings  # noqa: E402
from thesis.research import move_explainer as E  # noqa: E402


def verify_sources(conn,case):
    if case['origin']=='authored':return
    for source in case['sources'].values():
        if source['kind']=='news':
            row=one(conn,'SELECT v.content_hash FROM document_versions v JOIN documents d ON d.id=v.document_id '
                "JOIN sources s ON s.id=d.source_id WHERE v.id=%s AND s.entitlement IN ('finnhub-pitch','public-news')",(source['id'],))
            valid=row and row['content_hash']==source['version']
        else:
            row=one(conn,'SELECT headline,summary,url FROM world_news_articles WHERE id=%s',(source['id'],))
            permitted=one(conn,"SELECT id FROM sources WHERE id='finnhub-news' AND entitlement='finnhub-pitch'")
            valid=permitted and row and row['headline']==source['headline'] and row['summary'][:400]==source['excerpt'] and row['url']==source['url']
        if not valid:raise ValueError('Frozen source access or the consumed source version changed.')


def requests(manifest):
    if manifest.get('model')!=settings.OPENAI_EXPLAINER_MODEL:
        raise ValueError('This trial is restricted to the priced GPT-5.5 snapshot.')
    cases=manifest.get('cases')
    if not isinstance(cases,list) or len(cases)!=10:
        raise ValueError('Use exactly ten frozen authored/real cases.')
    seen=set();result=[]
    for case in cases:
        identity=case.get('id')
        if not isinstance(identity,str) or not re.fullmatch(r'[a-z0-9-]{1,50}',identity) or identity in seen:
            raise ValueError('Use distinct bounded case identities.')
        seen.add(identity)
        if case.get('origin') not in ('authored','saved_real') or not isinstance(case.get('sources'),dict):
            raise ValueError('Every case must distinguish authored and saved-real evidence.')
        content=dict(move=case['move'],headlines=[dict(source_id=k,**s) for k,s in case['sources'].items()])
        result.append((case,E.request_for(content,model=manifest['model'])))
    return result


def estimate(manifest):
    prepared=requests(manifest)
    amounts=[Decimal(ledger.estimate(body))/ledger.NANO for _,body in prepared]
    return dict(model=manifest['model'],cases=len(prepared),
                summed_reservation_maximum_usd=str(sum(amounts)),largest_reservation_usd=str(max(amounts)),
                paid_calls=0,app_research_writes=0,automatic_retries=0)


def remaining_requests(manifest,prepared,previous):
    """Explicit continuation skips every saved valid answer; never resends a call."""
    previous=Path(previous)
    if json.loads((previous/'manifest.json').read_text())!=manifest:
        raise ValueError('The continuation must use the identical frozen manifest.')
    report=json.loads((previous/'validation.json').read_text())
    if Decimal(report['unresolved_maximum_usd'])!=0:
        raise ValueError('An uncertain paid request cannot be continued automatically.')
    retained=[];pending=[]
    for case,body in prepared:
        response=previous/(case['id']+'.response.json')
        request=previous/(case['id']+'.request.json')
        if response.exists():
            parsed=E.parse({'response_body':json.loads(response.read_text())},case['sources'])
            retained.append(dict(case=case['id'],origin=case['origin'],passed=True,
                                 cause=parsed['cause'],reused_saved_response=True,paid_usd='0'))
        elif request.exists():
            raise ValueError('A previously attempted request cannot be sent again.')
        else:pending.append((case,body))
    return pending,retained


def run(manifest,output,cap,*,transport=None,remaining_after=None):
    if not isinstance(cap,Decimal) or not cap.is_finite() or not 0<cap<=Decimal('2'):
        raise ValueError('This trial needs a positive cap of at most US$2.')
    prepared=requests(manifest)
    retained=[]
    if remaining_after is not None:
        prepared,retained=remaining_requests(manifest,prepared,remaining_after)
    if transport is None and os.environ.get('THESIS_TEST_OFFLINE')=='true':
        raise ValueError('Offline tests cannot dispatch a live trial.')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    manifest_hash=hashlib.sha256(ledger.canonical(manifest).encode()).hexdigest()
    report=dict(model=manifest['model'],manifest_sha256=manifest_hash,planned=10,calls=retained,
                paid_usd='0',unresolved_maximum_usd='0',cap_usd=str(cap),completed=False,
                app_research_writes=0,automatic_retries=0,attempted=0)
    def save():
        (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');save()
    with ExitStack() as stack:
        if transport is None:
            configured=settings.settings()
            chosen=dict(configured,THESIS_MOVE_EXPLAINER_MODEL=manifest['model'])
            if settings.select(chosen)!=(settings.PROVIDER,settings.MODEL,settings.REASONING_MODEL):
                raise ValueError('The running trial must retain the selected bulk/quick pair.')
            stack.enter_context(patch.object(settings,'EXPLAINER_MODEL',manifest['model']))
            stack.enter_context(patch.object(settings,'settings',lambda:chosen))
        for case,body in prepared:
            ceiling=Decimal(ledger.estimate(body))/ledger.NANO
            if Decimal(report['paid_usd'])+ceiling>cap:
                report['stopped']='cap_before_dispatch';break
            key=f"experiment:move-explainer:{output.resolve()}:{manifest_hash}:{case['id']}"
            with transaction(consistent=True) as conn:
                try:verify_sources(conn,case)
                except ValueError:
                    report['stopped']='source_access_or_version_changed';break
                if one(conn,'SELECT id FROM model_calls WHERE request_key=%s',(key,)):
                    raise ValueError('This request was already attempted; no automatic retry.')
            (output/(case['id']+'.request.json')).write_text(json.dumps(body,indent=2)+'\n')
            report['attempted']+=1;save()
            try:
                call=ledger.execute(key,E.POLICY,body,transport=transport)
            except Exception as error:
                report['stopped']=type(error).__name__
                with transaction(consistent=True) as conn:
                    held=one(conn,'SELECT status,reserved_nano_usd FROM model_calls WHERE request_key=%s',(key,))
                if held and held['status'] in ('dispatched','unresolved'):
                    report['unresolved_maximum_usd']=str(Decimal(held['reserved_nano_usd'])/ledger.NANO)
                break
            charged=Decimal(call['charged_nano_usd'])/ledger.NANO
            report['paid_usd']=str(Decimal(report['paid_usd'])+charged)
            save()
            (output/(case['id']+'.response.json')).write_text(json.dumps(call['response_body'],indent=2)+'\n')
            row=dict(case=case['id'],origin=case['origin'],paid_usd=str(charged),passed=False)
            try:
                result=E.parse(call,case['sources'])
            except Exception:
                report['calls'].append(row);report['stopped']='citation_or_output_failure_no_retry';break
            row.update(passed=True,cause=result['cause'],sentences=len(result['sentences']),
                       expected_cause_match=None if case.get('expected_cause') is None else case['expected_cause']==result['cause'])
            report['calls'].append(row);save()
            print(json.dumps(row),flush=True)
        report['completed']=len(report['calls'])==10 and all(c['passed'] for c in report['calls'])
        report['passed']=sum(c['passed'] for c in report['calls'])
        save()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--cap-usd',type=Decimal,default=Decimal('2'))
    parser.add_argument('--remaining-after',type=Path,
                        help='Explicitly approved continuation: reuse saved valid answers, send only unattempted cases.')
    args=parser.parse_args();manifest=json.loads(args.manifest.read_text())
    if args.execute:
        if args.output is None:parser.error('--execute requires a new --output directory')
        result=run(manifest,args.output,args.cap_usd,remaining_after=args.remaining_after)
        print(json.dumps({k:v for k,v in result.items() if k!='calls'}))
    else:print(json.dumps(estimate(manifest),indent=2))
