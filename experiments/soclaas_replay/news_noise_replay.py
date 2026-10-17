"""File-only replay of company-news publications, routing and bounded messages.

Requires complete evaluated readings, never invents importance for missing data.
No database, provider or Telegram calls. Sent means hypothetical formatter output.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, time, timedelta, timezone
from html import escape
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
import argparse
import json

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.soclaas_replay import noise_replay_readiness as N  # noqa:E402
from thesis.monitoring import (news_watch as W, alert_routing as R, telegram_stories as G,
    telegram_message as M, daily_telegram as DT)  # noqa:E402
from thesis.research import sentiment as S, sentiment_tasks as T, coverage  # noqa:E402
from thesis.research.catalogue import mentions  # noqa:E402

POLICY = 'company-news-noise-replay-1'
SGT = ZoneInfo('Asia/Singapore')
FOOTER = ('Open Fledge on your Mac → Updates → Daily recaps for all saved updates and evidence.\n'
          'Research alerts · not buy/sell instructions.')
LOW_VALUE = {'opinion','comparison','price_recap','unclear'}


def frame_key(frame):
    return frame['instrument_id']+'@'+N.instant(frame['cutoff']).isoformat()


def canonical_sources(capture, company, ids):
    """Production news rank and exact-content selection, before batch labels."""
    def rank(source):
        score=2 if mentions(source['title'],company['symbol'],company['name']) else (
            1 if mentions(source['text'],company['symbol'],company['name']) else 0)
        return score,N.instant(source['published_at']),source['id']
    selected=[];seen=set()
    for source in sorted((capture['sources'][sid] for sid in ids),key=rank,reverse=True):
        if source['content_hash'] in seen:continue
        seen.add(source['content_hash']);selected.append(dict(deepcopy(source),label='item_'+str(len(selected)+1)))
    return selected


def baseline_sources(capture, company):
    start=N.instant(capture['window_start'])
    return canonical_sources(capture,company,[sid for sid,s in capture['sources'].items()
        if s['instrument_id']==company['instrument_id'] and N.instant(s['available_at'])<=start
        and start-timedelta(days=7)<=N.instant(s['published_at'])<=start])


def check_reading(reading, capture, company, cutoff, *, new=(), expected_sources):
    """Check exact frozen evidence and complete items before producing any alert."""
    packet, result = reading['packet'], reading['result']
    if (packet['instrument_id'] != company['instrument_id'] or packet['company'] != {
            k:company[k] for k in ('symbol','name')} or N.instant(packet['cutoff']) != cutoff
            or result.get('prompt_version') != T.PROMPT
            or result.get('summary_policy') != S.POLICY
            or result.get('guard_policy') != N.sentiment_guards.POLICY
            or any(packet.get(k)!=v for k,v in N.POLICIES.items())
            or (result.get('batching') or {}).get('policy') != T.POLICY):
        raise ValueError('A replay reading has the wrong company, cutoff or task contract.')
    source_ids = [s['id'] for s in packet['sources']]
    if len(set(source_ids)) != len(source_ids) or len({s['label'] for s in packet['sources']}) != len(source_ids):
        raise ValueError('A replay reading needs distinct source IDs and labels.')
    if [(s['id'],s['label']) for s in packet['sources']]!=[(s['id'],s['label']) for s in expected_sources]:
        raise ValueError('A replay reading must retain the whole ranked, deduplicated news sample.')
    items = result['items']
    if Counter(i['source_id'] for i in items) != Counter(source_ids):
        raise ValueError('Every replay source needs exactly one evaluated item.')
    by_id = {s['id']:s for s in packet['sources']}
    for source in packet['sources'] + packet.get('comparison_sources',[]):
        frozen = capture['sources'].get(source['id'])
        if (not frozen or source['instrument_id'] != company['instrument_id']
                or source['content_hash']!=frozen['content_hash'] or source.get('url')!=frozen.get('url')
                or N.sentiment_reuse.content_key(source) != N.sentiment_reuse.content_key(frozen)
                or N.model_source(source)['passages'] != source['passages']
                or N.instant(source['available_at']) > cutoff
                or not cutoff-timedelta(days=7) <= N.instant(source['published_at']) <= cutoff):
            raise ValueError('Replay evidence changed or was unavailable at the cutoff.')
    for item in items:
        source = by_id[item['source_id']]
        # Old tone provenance is retained; no new-prompt accuracy is inferred.
        record = dict(packet=packet,result=result)
        if item['id'] != source['label'] or not N.candidate(record, source, item):
            raise ValueError('A replay item lacks valid saved tone/evidence provenance.')
        if item['source_id'] in new and not item.get('prefilter'):
            value = item.get('importance') or {}
            if value.get('policy') != T.POLICY or value.get('level') not in {'high','medium','low'}:
                raise ValueError('New replay news has no evaluated importance; do not assume low.')
            own = {p['id']:p['quote'] for p in source['passages']}
            for citation in value.get('citations',[]):
                if (citation.get('source_id') != source['id'] or citation.get('passage_id') not in own
                        or citation.get('quote') != own[citation['passage_id']]):
                    raise ValueError('Replay importance does not cite its own frozen evidence.')
            for citation in (item.get('reporting_basis') or {}).get('citations',[]):
                if (citation.get('source_id') != source['id'] or citation.get('passage_id') not in own
                        or citation.get('quote') != own[citation['passage_id']]):
                    raise ValueError('Replay reporting does not cite its own frozen evidence.')
    # Recheck optional suppression links through the same code-owned guards.
    all_sources={s['id']:s for s in packet['sources']+packet.get('comparison_sources',[])}
    links=result.get('coverage_links',[]);raw=[]
    for link in links:
        own=all_sources.get(link['source_id']);prior=all_sources.get(link['reference_source_id'])
        if not own or not prior:raise ValueError('A replay comparison references unavailable evidence.')
        raw.append(coverage.Link(item_id=own['label'],reference_id=prior['label'],relation=link['relation'],
            explanation='Retained replay comparison',item_passages=[c['passage_id'] for c in link['citations']],
            reference_passages=[c['passage_id'] for c in link['reference_citations']]))
    restored=coverage.render(raw,packet,items)
    fields=('source_id','reference_source_id','relation','repeat_suppression_allowed','review_note',
            'change_evidence','citations','reference_citations')
    if [{k:l.get(k) for k in fields} for l in restored]!=[{k:l.get(k) for k in fields} for l in links]:
        raise ValueError('Replay comparison evidence or suppression guards changed.')
    if result['summary'] != S.summarize(items,packet['sources'],result.get('coverage_links',[]),packet.get('comparison_sources',[])):
        raise ValueError('The replay summary does not match the complete evaluated sample.')


def publication(payload, reading, index):
    packet = reading['packet']
    return dict(id=N.digest(dict(frame=index,kind=payload['kind'])),kind='company',
        created_at=N.instant(packet['cutoff']),title=payload['title'],
        detail=dict(symbol=packet['company']['symbol'],preview=False,withheld=False,
            payload=deepcopy(payload),sources=[dict(s,source=s.get('publisher')) for s in packet['sources']]),
        analysis_index=index)


def filtered(record, reading, claims, now, *, local=(), immediate=False):
    """Same pure keys, item ordering and high-only selection as the live guard."""
    record = deepcopy(record)
    sources = {s['id']:s for s in reading['packet']['sources']}
    done = set(local) | {key for sent,keys in claims if sent > now-timedelta(hours=24) for key in keys}
    kept=[]; within=set(); mapping={}
    for item in record['detail']['payload']['items']:
        if immediate and R.importance(item) != 'high': continue
        source = sources[item['source_id']]
        if G.source_keys(reading,source) & (done|within): continue
        keys = G.source_keys(reading,source,for_claim=True)
        kept.append(item); mapping[source['id']]=keys;within.update(keys)
    if not kept: return None
    record['detail']['payload']['items']=kept
    return record,mapping


def replay(capture, evaluated):
    N.validate(capture)
    if evaluated.get('input_fingerprint') != capture['fingerprint']:
        raise ValueError('Evaluated readings belong to a different frozen input.')
    companies = {c['instrument_id']:c for c in capture['companies']}
    start,end = N.instant(capture['window_start']),N.instant(capture['window_end'])
    readings = evaluated.get('frames',{})
    expected = {frame_key(f) for f in capture['frames']}
    if set(readings) != expected:
        raise ValueError('All frozen frames must be evaluated; missing frames are not quiet days.')
    previous = {}; seen = {iid:set() for iid in companies}; records=[]; messages=[]; claims=[]; pending=[]
    for iid,company in companies.items():
        if capture['baseline_counts'].get(company['symbol'],0):
            baseline = evaluated.get('baselines',{}).get(iid)
            if not baseline: raise ValueError('An existing pre-window baseline needs its evaluated sample.')
            check_reading(baseline,capture,company,start,expected_sources=baseline_sources(capture,company))
            previous[iid] = baseline
            for source in baseline['packet']['sources']:
                seen[iid].update((source['channel'],key) for key in coverage.observed_keys(baseline,source))
    digest_end = datetime.combine(start.astimezone(SGT).date(),time(7),SGT).astimezone(timezone.utc)
    if digest_end <= start: digest_end += timedelta(days=1)
    digest_start = start
    analyses = dict(readings)

    def emit_digest(until):
        nonlocal digest_end,digest_start,pending
        while digest_end <= until:
            members = [r for r in pending if r['created_at'] < digest_end]
            pending = [r for r in pending if r['created_at'] >= digest_end]
            parts=['<b>Fledge · Daily recap</b>',escape(DT.stamp(digest_start)+'–'+DT.stamp(digest_end))]
            shown=[]; linked=set(); local=set(); omitted=0;duplicates=0
            for record in members:
                if len(shown) >= DT.MAX_ITEMS: omitted+=1;continue
                value = filtered(record,analyses[record['analysis_index']],claims,digest_end,local=local)
                if not value: duplicates+=1;continue
                kept,mapping=value; primary=[]; block=DT.summary(kept,len(shown)+1,shown=primary)
                if not block: omitted+=1;continue
                text=block[0]; links=[]
                for url,name in block[1]:
                    if url not in linked and url not in {u for u,_ in links} and len(linked)+len(links)<2:
                        links.append((url,name))
                if links: text+='\n'+'\n'.join(f'<a href="{escape(url,quote=True)}">{escape(name)}</a>' for url,name in links)
                if M.visible_units('\n\n'.join(parts+[text,FOOTER]))>3400: omitted+=1;continue
                parts.append(text);linked.update(u for u,_ in links)
                keys={k for sid in primary for k in mapping.get(sid,())};local.update(keys)
                shown.append(dict(event_id=record['id'],source_ids=primary))
            if shown:
                if omitted: parts.append(f'{omitted} more saved updates are in this recap in Fledge.')
                if duplicates:
                    noun='update is' if duplicates==1 else 'updates are'
                    parts.append(f'{duplicates} repeated {noun} omitted here; the full recap remains in Fledge.')
                parts.append(FOOTER);text='\n\n'.join(parts)
                if M.visible_units(text)>3800: raise ValueError('Replay recap exceeds the live message bound.')
                messages.append(dict(id=N.digest(dict(kind='digest',at=digest_end.isoformat())),kind='digest',
                    at=digest_end.isoformat(),shown=shown,message=text))
                claims.append((digest_end,local))
            digest_start=digest_end;digest_end+=timedelta(days=1)

    for frame in capture['frames']:
        index=frame_key(frame);current=readings[index];iid=frame['instrument_id'];at=N.instant(frame['cutoff'])
        emit_digest(at)
        expected_sources=canonical_sources(capture,companies[iid],frame['source_ids']+frame['comparison_source_ids'])
        check_reading(current,capture,companies[iid],at,
            new=() if frame['initial_baseline'] else frame['source_ids'],expected_sources=expected_sources)
        before=previous.get(iid)
        proposals=R.important_reporting(before,current,seen[iid])
        ordinary=W.changes(before,current,seen[iid]) if before else []
        proposal_ids={i['source_id'] for p in proposals for i in p['items']}
        for payload in ordinary+proposals:
            record=publication(payload,current,index);decision=R.classify(record)
            own={i['source_id'] for i in payload['items']}
            if payload['kind']!='important_reporting' and own and own<=proposal_ids:
                decision=dict(severity='low',channel='app',reason='Covered by the same company importance update.',items=[])
            record['routing']=decision;records.append(record)
            if decision['channel']=='digest': pending.append(record)
            elif decision['channel']=='telegram':
                value=filtered(record,current,claims,at,immediate=True)
                if not value: continue
                kept,mapping=value;primary=[];text=M.render(kept,shown=primary)
                if not primary: raise ValueError('No primary evidence fits the immediate replay message.')
                messages.append(dict(id=N.digest(dict(event=record['id'])),kind='immediate',at=at.isoformat(),
                    shown=[dict(event_id=record['id'],source_ids=primary)],message=text))
                claims.append((at,{k for sid in primary for k in mapping[sid]}))
        previous[iid]=current
        for source in current['packet']['sources']:
            seen[iid].update((source['channel'],key) for key in coverage.observed_keys(current,source))
    # Follow only pending messages to the next scheduled recap. No later source
    # input is read, and this tail is separate from the seven input dates.
    tail = digest_end if pending else end
    emit_digest(max(end,tail))
    observed_days={N.instant(f['cutoff']).astimezone(SGT).date().isoformat() for f in capture['frames']}
    report=dict(policy=POLICY,input_fingerprint=capture['fingerprint'],completed_input_days=len(observed_days),
        input_window_start=start.isoformat(),input_window_end=end.isoformat(),
        digest_follow_through_until=max(end,tail).isoformat(),
        publications=[dict(r,created_at=r['created_at'].isoformat()) for r in records],messages=messages,
        counts=dict(publications=len(records),messages=len(messages),
            immediate=sum(m['kind']=='immediate' for m in messages),daily_recaps=sum(m['kind']=='digest' for m in messages)),
        noise_gate='pending_independent_review',paid_calls=0,telegram_http_calls=0,app_writes=0,
        limitations=['Retrospective company-news-only counterfactual for the fixed captured portfolio.',
            'Source availability frames are not observed watch dispatch times; no latency or delivery claim.',
            'Assumes successful hypothetical delivery; live rejection/uncertainty paths have separate tests.',
            'Excludes private ideas, conditions, social-tone alerts, price events and cost notifications.',
            'Later saved tone provenance is retained; this does not prove new-prompt owner accuracy.',
            'Independent source-form review is required; classifier low categories cannot grade themselves.'])
    report['fingerprint']=N.digest(report)
    return report


def audit(report, annotations):
    if N.digest({k:v for k,v in report.items() if k!='fingerprint'}) != report.get('fingerprint'):
        raise ValueError('The frozen replay report changed.')
    shown={sid for m in report['messages'] for event in m['shown'] for sid in event['source_ids']}
    labels=annotations.get('labels',{})
    if (annotations.get('report_fingerprint')!=report['fingerprint']
            or annotations.get('independent_excerpt_review') is not True or set(labels)!=shown
            or any(value not in LOW_VALUE|{'substantive'} for value in labels.values())):
        raise ValueError('Every displayed source needs independent review of the exact replay.')
    total=len(report['messages'])
    low=sum(any(labels[sid] in LOW_VALUE for event in m['shown'] for sid in event['source_ids']) for m in report['messages'])
    return dict(messages=total,low_value_messages=low,low_value_percent=100*low/total if total else None,
        passed=report['completed_input_days']==7 and bool(total) and low*10<=total,scope='company-news counterfactual only',
        owner_label_quality='pending_separate_50_source_check')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path);parser.add_argument('evaluated',type=Path)
    parser.add_argument('output',type=Path);parser.add_argument('--annotations',type=Path)
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Choose a new output path; retained replay evidence is not overwritten.')
    report=replay(json.loads(args.capture.read_text()),json.loads(args.evaluated.read_text()))
    result=dict(replay=report)
    if args.annotations:result['independent_audit']=audit(report,json.loads(args.annotations.read_text()))
    with args.output.open('x') as output:output.write(json.dumps(result,default=str,indent=2)+'\n')
    print(json.dumps(report['counts'],indent=2))
