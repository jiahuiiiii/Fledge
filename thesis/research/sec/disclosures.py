"""Immutable original filings and filed earnings releases, with visible gaps."""
import hashlib
import re
from datetime import datetime, timedelta, timezone, date
from uuid import uuid4, uuid5, NAMESPACE_URL
from psycopg.types.json import Jsonb
from thesis.db import transaction, one, rows
from thesis.service import Conflict
from . import client
from .disclosure_text import archive_url, parse, exhibits, METHOD

SOURCE='sec-disclosures'


def fence(iid, attempt):
    with transaction(source=True) as conn:
        state=one(conn,'SELECT attempt_id,lease_until FROM disclosure_refresh_state WHERE instrument_id=%s',(iid,))
        allowed=one(conn,"SELECT 1 FROM sources WHERE id=%s AND entitlement='sec-public'",(SOURCE,))
        if not allowed or not state or state['attempt_id']!=attempt or not state['lease_until'] or state['lease_until']<datetime.now(timezone.utc):
            raise ValueError('The original-filing collection was stopped, replaced or expired.')


def plan(submissions, cik, now):
    if int(submissions.get('cik',0))!=int(cik):raise ValueError('Filing metadata belongs to another issuer.')
    recent=submissions.get('filings',{}).get('recent',{})
    fields=['accessionNumber','form','filingDate','reportDate','primaryDocument','acceptanceDateTime']
    if not all(isinstance(recent.get(k),list) for k in fields) or len({len(recent[k]) for k in fields})!=1:
        raise ValueError('Filing metadata is incomplete.')
    candidates=[]
    for i in range(len(recent['form'])):
        form=recent['form'][i]
        if form not in ('10-K','10-K/A','10-Q','10-Q/A','20-F','20-F/A','40-F','40-F/A','8-K','8-K/A'):continue
        if any(not isinstance(recent[key][i],str) for key in fields):raise ValueError('Filing metadata has unsupported field types.')
        accepted=datetime.fromisoformat(recent['acceptanceDateTime'][i].replace('Z','+00:00'))
        if not accepted.tzinfo or accepted>now:continue
        # Only results-of-operations 8-Ks, not every corporate event.
        items=recent.get('items',[])
        if not isinstance(items,list) or (i<len(items) and not isinstance(items[i],str)):raise ValueError('Filing event metadata is malformed.')
        if form.startswith('8-K') and (i>=len(items) or '2.02' not in items[i] or now-accepted>timedelta(days=120)):continue
        slot='annual' if form.startswith(('10-K','20-F','40-F')) else 'quarter' if form.startswith('10-Q') else 'earnings_filing'
        period_end=date.fromisoformat(recent['reportDate'][i]) if slot!='earnings_filing' else accepted.date()
        if period_end>accepted.date():continue
        candidates.append(dict(slot=slot,form=form,accession=recent['accessionNumber'][i],published_at=accepted,period_end=period_end.isoformat(),
                               url=archive_url(cik,recent['accessionNumber'][i],recent['primaryDocument'][i]),
                               filed_on=recent['filingDate'][i]))
    selected={}
    for item in sorted(candidates,key=lambda x:(x['period_end'],x['published_at'],x['accession'])):selected[item['slot']]=item
    result = [selected[slot] for slot in ('annual','quarter','earnings_filing') if slot in selected]
    # Retain earlier amendments in the same current period so resolution can
    # inspect every intervening change. Reuse the normal lease/clock/denial path.
    for slot in ('annual', 'quarter'):
        latest = selected.get(slot)
        if not latest or not latest['form'].endswith('/A'):
            continue
        earlier = [item for item in candidates if item['slot'] == slot and item['period_end'] == latest['period_end'] and item['form'] == latest['form'] and item['accession'] != latest['accession']]
        for item in sorted(earlier, key=lambda x: (x['published_at'], x['accession']))[-7:]:
            result.append(dict(item, slot=f'{slot}_amendment_{item["accession"]}'))
    return result


def commit(conn, iid, item, raw, data, now, name):
    digest=hashlib.sha256(raw).hexdigest()
    did=uuid5(NAMESPACE_URL,f'thesis:disclosure:{iid}:{item["url"]}:{digest}')
    # Exact A -> B -> A returns reuse the original availability timestamp.
    data=dict(data,report_period_end=item.get('period_end'))
    current=one(conn,'SELECT d.published_at,d.data FROM disclosure_current c JOIN disclosure_documents d ON d.id=c.document_id WHERE c.instrument_id=%s AND c.slot=%s',(iid,item['slot']))
    if current:
        previous_period=current['data'].get('report_period_end');incoming_period=item.get('period_end')
        if previous_period and incoming_period and incoming_period<previous_period:raise ValueError('Filing metadata would move the reporting period backwards.')
        if (not previous_period or not incoming_period) and current['published_at']>item['published_at']:raise ValueError('Filing metadata predates a retained document without comparable reporting-period metadata.')
    conn.execute('INSERT INTO disclosure_documents(id,instrument_id,source_id,slot,accession,form,url,headline,published_at,available_at,content_hash,raw_html,data) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                 (did,iid,SOURCE,item['slot'],item['accession'],item['form'],item['url'],f'{name} · {item["form"]} · {item["slot"].replace("_"," ")}',item['published_at'],now,digest,raw,Jsonb(data)))
    # Selection follows reporting periods, so an older-period amendment cannot
    # replace a newer report merely because its acceptance date is later.
    conn.execute('INSERT INTO disclosure_current VALUES(%s,%s,%s,%s) ON CONFLICT(instrument_id,slot) DO UPDATE SET document_id=excluded.document_id,checked_at=excluded.checked_at',(iid,item['slot'],did,now))
    return str(did)


def refresh(iid, *, fetcher=None, submissions=None):
    if fetcher is None:client.identity()
    now=datetime.now(timezone.utc);attempt=uuid4()
    with transaction(source=True) as conn:
        company=one(conn,'SELECT c.cik,i.name FROM sec_companies c JOIN instruments i ON i.id=c.instrument_id WHERE c.instrument_id=%s',(iid,))
        if not company:raise ValueError('Choose a registered company for original filings.')
        if not one(conn,"SELECT 1 FROM sources WHERE id=%s AND entitlement='sec-public'",(SOURCE,)):
            raise ValueError('Original-filing source access is unavailable.')
        conn.execute('INSERT INTO disclosure_refresh_state(instrument_id) VALUES(%s) ON CONFLICT DO NOTHING',(iid,))
        state=one(conn,'SELECT * FROM disclosure_refresh_state WHERE instrument_id=%s FOR UPDATE',(iid,))
        if state['last_attempt_at'] and now-state['last_attempt_at']<timedelta(minutes=15):
            raise Conflict('Original filings were checked recently. Wait 15 minutes between attempts.')
        if submissions is None:
            bundle=one(conn,'SELECT p.payload,c.checked_at FROM sec_payload_current c JOIN source_payloads p ON p.id=c.payload_id AND p.instrument_id=c.instrument_id WHERE c.instrument_id=%s',(iid,))
            if not bundle or now-bundle['checked_at']>timedelta(hours=24):
                raise ValueError('Refresh structured filings first to obtain current issuer metadata.')
            submissions=bundle['payload']['submissions']
        conn.execute('UPDATE disclosure_refresh_state SET attempt_id=%s,last_attempt_at=%s,lease_until=%s WHERE instrument_id=%s',(attempt,now,now+timedelta(minutes=3),iid))
    coverage=[];saved=0
    try:
        items=plan(submissions,company['cik'],now)
        for slot in ('annual','quarter','earnings_filing'):
            if slot not in {i['slot'] for i in items}:coverage.append(dict(slot=slot,status='missing',message='No supported filing in the retained metadata.'))
        read=fetcher or client.fetch_document
        for item in items:
            fence(iid,attempt)
            if '_amendment_' in item['slot']:
                with transaction(source=True, consistent=True) as conn:
                    retained = one(conn, 'SELECT id FROM disclosure_documents WHERE instrument_id=%s AND accession=%s AND url=%s ORDER BY available_at DESC LIMIT 1', (iid,item['accession'],item['url']))
                if retained:
                    coverage.append(dict(slot=item['slot'],status='available',document_id=str(retained['id'])));continue
            raw=read(item['url']);data=parse(raw,form=item['form'],cik=company['cik'])
            documents=[(item,raw,data)]
            if item['slot']=='earnings_filing':
                links=exhibits(data,item['url'])
                if not links:coverage.append(dict(slot='earnings_release',status='missing',message='No explicit Exhibit 99 HTML link in this results filing.'))
                for index,url in enumerate(links):
                    # Stop after the first failure. Do not try another host or
                    # another exhibit to work around a rejected request.
                    fence(iid,attempt)
                    release=read(url);parsed=parse(release,form='earnings-release',cik=company['cik'])
                    if not re.search(r'financial results|quarter.{0,50}results|results of operations|revenue|earnings',parsed['body'],re.I):
                        coverage.append(dict(slot=f'earnings_release_{index+1}',status='unsupported',message='Exhibit 99 does not contain recognizable results text.'))
                        continue
                    documents.append((dict(item,slot=f'earnings_release_{index+1}',form='earnings-release',url=url),release,parsed))
            with transaction(source=True) as conn:
                state=one(conn,'SELECT * FROM disclosure_refresh_state WHERE instrument_id=%s FOR UPDATE',(iid,))
                checked=datetime.now(timezone.utc)
                if state['attempt_id']!=attempt or state['lease_until']<checked or not one(conn,"SELECT 1 FROM sources WHERE id=%s AND entitlement='sec-public'",(SOURCE,)):
                    raise ValueError('The original-filing collection was stopped, replaced or expired.')
                for metadata,body,parsed in documents:
                    did=commit(conn,iid,metadata,body,parsed,checked,company['name'])
                    coverage.append(dict(slot=metadata['slot'],status='available',document_id=did));saved+=1
        if not items:raise ValueError('No supported original filings in the retained metadata.')
        message=None
    except (ValueError,client.SourceFailure):
        message='Original-filing collection could not finish. Saved documents are retained; no automatic retry was made.'
        coverage.append(dict(slot='collection',status='failed',message=message))
    with transaction(source=True) as conn:
        state=one(conn,'SELECT * FROM disclosure_refresh_state WHERE instrument_id=%s FOR UPDATE',(iid,))
        if state['attempt_id']!=attempt:raise ValueError('This original-filing attempt was replaced.')
        conn.execute('UPDATE disclosure_refresh_state SET lease_until=NULL,last_success_at=CASE WHEN %s THEN now() ELSE last_success_at END,last_error=%s,coverage=%s WHERE instrument_id=%s',
                     (message is None,message,Jsonb(coverage),iid))
    return dict(status='partial' if message or any(c['status']!='available' for c in coverage) else 'ready',message=message or f'{saved} original filing documents checked.',coverage=coverage)


def present(conn, iid, *, include_text=False):
    if not one(conn,"SELECT 1 FROM sources WHERE id=%s AND entitlement='sec-public'",(SOURCE,)):
        return dict(status='unavailable',documents=[],message='Original-filing source access is unavailable.')
    state=one(conn,'SELECT * FROM disclosure_refresh_state WHERE instrument_id=%s',(iid,))
    documents=rows(conn,'SELECT d.id,d.slot,d.form,d.accession,d.url,d.headline,d.published_at,d.available_at,d.data,c.checked_at FROM disclosure_current c JOIN disclosure_documents d ON d.id=c.document_id AND d.instrument_id=c.instrument_id WHERE c.instrument_id=%s ORDER BY d.slot',(iid,))
    earnings=next((d['accession'] for d in documents if d['slot']=='earnings_filing'),None)
    documents=[d for d in documents if '_amendment_' not in d['slot'] and (not d['slot'].startswith('earnings_release') or d['accession']==earnings)]
    for item in documents:
        data=item.pop('data')
        item.update(method=data['method'],sections=data['sections'],limitations=data['limitations'],passage_count=len(data['passages']))
        if include_text:item.update(body=data['body'],passages=data['passages'])
    partial=state and (state['last_error'] or any(c['status']!='available' for c in state['coverage']))
    return dict(status='partial' if partial else 'available' if documents else 'empty',documents=documents,source_status=state,
                message=state['last_error'] if state else 'Collect original filings to prepare the business brief.')


def document(iid, did):
    with transaction() as conn:
        if not one(conn,"SELECT 1 FROM sources WHERE id=%s AND entitlement='sec-public'",(SOURCE,)):raise ValueError('Original-filing source access is unavailable.')
        record=one(conn,'SELECT id,slot,form,accession,url,headline,published_at,available_at,data FROM disclosure_documents WHERE instrument_id=%s AND id=%s',(iid,did))
        if not record:raise ValueError('This original document is not available for the company.')
        return record
