"""General amendment resolution: authored identities/amounts, no live requests."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from uuid import uuid4

import pytest
from psycopg.types.json import Jsonb
from thesis.db import transaction, one
from thesis.research.sec import amendments, disclosures
from thesis.research.sec.disclosure_text import parse, archive_url
from thesis.research.sec.performance import normalize_performance, present as saved_performance
from thesis.research.sec.financial_story import normalize_story
from thesis.research.sec.financial_depth import normalize_depth
from thesis.research.sec.service import add_company
from test_performance import financial_bundle
from test_sec_fundamentals import apply, CIK, NOW

UNCHANGED = 'This amendment does not amend, update or change the consolidated financial statements. It supplies the information required by Part III of the annual report.'

def present(conn,iid):
    return saved_performance(conn,iid,resolve_amendments=True)


def amended(kind='annual', cik=CIK):
    b=financial_bundle()
    b['companyfacts']['cik']=b['submissions']['cik']=cik
    r=b['submissions']['filings']['recent'];index=0 if kind=='annual' else 1
    for values in r.values():values.append(values[index])
    r['form'][-1]+='/A';r['accessionNumber'][-1]='0000789019-25-000003'
    r['filingDate'][-1]='2025-11-01';r['acceptanceDateTime'][-1]='2025-11-01T20:00:00Z'
    return b


def document(b, note=UNCHANGED, table='', accession=None):
    filings=amendments.filing_rows(b['submissions'],NOW)
    f=next(f for f in filings if f['accessionNumber']==accession) if accession else filings[-1]
    raw=('<html><body><xbrli:unit><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit><h1>Explanatory Note</h1><p>'+note+'</p><h2>Part III</h2><p>'+('Corporate governance information. '*10)+'</p>'+table+'</body></html>').encode()
    data=parse(raw,form=f['form'],cik=int(b['companyfacts']['cik']));data['report_period_end']=f['end'].isoformat()
    return dict(id=str(uuid4()),accession=f['accessionNumber'],form=f['form'],url=archive_url(b['companyfacts']['cik'],f['accessionNumber'],f['primaryDocument']),published_at=f['accepted_at'],available_at=NOW,content_hash=hashlib.sha256(raw).hexdigest(),raw_html=raw,data=data)


def resolved(b, doc=None, docs=None, kind='annual'):
    docs=docs if docs is not None else {doc['accession']:doc} if doc else {}
    resolver=amendments.Resolver(b,int(b['companyfacts']['cik']),NOW,docs)
    f=next(f for f in reversed(resolver.filings) if f['form'].startswith('10-K' if kind=='annual' else '10-Q'))
    source=resolver.report(f);original=deepcopy(source)
    metrics,summary=resolver.resolve(f,source['metrics'])
    assert source==original
    return {m['key']:m for m in metrics},summary,resolver


@pytest.mark.parametrize('kind,cik',[('annual',789019),('annual',2488),('annual',999123),('quarter',789019)])
def test_explicit_unchanged_statement_works_for_any_issuer_or_period(kind,cik):
    b=amended(kind,cik);doc=document(b);m,s,_=resolved(b,doc,kind=kind)
    assert m['revenue']['value']==('500' if kind=='annual' else '120')
    assert m['revenue']['source_report']['form']==('10-K' if kind=='annual' else '10-Q')
    evidence=m['revenue']['filing_resolution']['amendments'][0]
    quote=evidence['support'][0]
    assert doc['data']['body'][quote['start']:quote['end']]==quote['quote']
    assert 'revenue' in s['retained'] and not s['needs_documents']


@pytest.mark.parametrize('note',[
 'Except for the corrected figures, this amendment does not change the financial statements.',
 'This amendment does not update the financial statements to reflect subsequent events.',
 'This amendment does not otherwise change the financial statements.',
 'This amendment does not change the financial statements. A material error requires restatement.',
 'No other changes are made to the original filing.',
 'This amendment will not change the financial statements once its review is complete.',
 'This amendment does not change the financial statements for 2024.',
 'If approved, this amendment does not change the financial statements.',
 'Our retention policy does not change the financial statements.',
])
def test_boilerplate_qualified_or_unclear_notes_do_not_authorize_inheritance(note):
    b=amended();m,s,_=resolved(b,document(b,note));assert m['revenue']['value'] is None
    assert 'scope is unclear' in m['revenue']['reason'] and not s['needs_documents']


def table(current='0.5',prior='0.4',unit='thousands',dates='September 30, 2025 | September 30, 2024'):
    return f'<table><tr><th>Years ended</th><th>{dates}</th></tr><tr><th>(In {unit})</th></tr><tr><td>Total revenue</td><td>$</td><td>{current}</td><td>$</td><td>{prior}</td></tr></table>'


def test_exact_dated_totals_prove_only_the_covered_figures():
    b=amended();m,s,r=resolved(b,document(b,'This amendment corrects a narrative disclosure.',table()))
    assert m['revenue_growth']['value']=='25.00' and m['revenue']['value']=='500'
    assert m['operating_income']['value'] is None and m['cash']['value'] is None
    # The same evidence fixes the annual financial chart and preserves evidence.
    story=normalize_story(b,CIK,NOW,r)
    row=next(x for x in story['annual'][-1]['metrics'] if x['key']=='revenue')
    assert row['value']=='500' and row['filing_resolution']['status']=='retained'


@pytest.mark.parametrize('change',['different','dates','unit','currency','hidden','conflicting_table','wrong_document','changed_hash','prior_only'])
def test_tables_and_document_identity_fail_closed(change):
    b=amended();raw=table()
    if change=='different':raw=table(current='0.6')
    if change=='dates':raw=table(dates='September 30, 2024 | September 30, 2023')
    if change=='unit':raw=table(unit='millions')
    if change=='hidden':raw='<div hidden>'+raw+'</div>'
    if change=='conflicting_table':raw+=table(current='0.6')
    if change=='prior_only':raw=raw.replace('Years ended','Years ended, as previously reported')
    d=document(b,'Narrative correction only.',raw)
    if change=='currency':
        d['raw_html']=d['raw_html'].replace(b'iso4217:USD',b'iso4217:EUR');d['content_hash']=hashlib.sha256(d['raw_html']).hexdigest()
    if change=='wrong_document':d['url']=d['url'].replace('000078901925000003','000078901925000099')
    if change=='changed_hash':d['content_hash']='wrong'
    m,_,_=resolved(b,d);assert m['revenue']['value'] is None


def add_corrected_facts(b, revenue=600):
    facts=b['companyfacts']['facts']['us-gaap'];r=b['submissions']['filings']['recent']
    for tag,data in facts.items():
        originals=[f for f in data['units']['USD'] if f['accn']=='0000789019-25-000001']
        for f in originals:
            f=dict(f,accn=r['accessionNumber'][-1],form=r['form'][-1],filed=r['filingDate'][-1])
            if tag.startswith('Revenue') and f['end']=='2025-09-30':f['val']=revenue
            data['units']['USD'].append(f)


def test_revised_figures_win_without_requiring_an_unchanged_note():
    b=amended();add_corrected_facts(b);m,s,_=resolved(b)
    assert m['revenue']['value']=='600' and m['revenue_growth']['value']=='50.0'
    assert m['revenue']['filing_resolution']['status']=='amended' and not m['revenue'].get('source_report')
    assert 'revenue' in s['amended']


def test_chain_uses_most_recent_revision_and_requires_every_intervening_amendment():
    b=amended();add_corrected_facts(b);first=b['submissions']['filings']['recent']['accessionNumber'][-1]
    r=b['submissions']['filings']['recent']
    for v in r.values():v.append(v[-1])
    r['accessionNumber'][-1]='0000789019-25-000004';r['filingDate'][-1]='2025-11-02';r['acceptanceDateTime'][-1]='2025-11-02T20:00:00Z'
    d=document(b);m,_,_=resolved(b,d)
    assert m['revenue']['value']=='600' and m['revenue']['source_report']['accession']==first
    # Without the first revision's facts or its text, the original cannot jump it.
    for data in b['companyfacts']['facts']['us-gaap'].values():data['units']['USD']=[f for f in data['units']['USD'] if f['accn']!=first]
    m,s,_=resolved(b,d);assert m['revenue']['value'] is None and s['needs_documents']
    d1=document(b,accession=first);m,_,_=resolved(b,docs={d1['accession']:d1,d['accession']:d})
    assert m['revenue']['value']=='500' and len(m['revenue']['filing_resolution']['amendments'])==2
    planned=disclosures.plan(b['submissions'],CIK,NOW)
    assert any(x['accession']==first and '_amendment_' in x['slot'] for x in planned)


def test_conflicting_amended_facts_are_not_masked_by_unchanged_statement():
    b=amended();add_corrected_facts(b)
    revenue=b['companyfacts']['facts']['us-gaap']['RevenueFromContractWithCustomerExcludingAssessedTax']['units']['USD']
    revenue.append(dict(revenue[-2],val=601))
    m,_,_=resolved(b,document(b));assert m['revenue']['value'] is None
    assert 'Conflicting' in m['revenue']['reason']


def test_retained_projection_is_read_only_and_both_source_permissions_apply(owner):
    b=amended();iid=add_company('MSFT')['instrument_id'];apply(iid,b);d=document(b)
    with transaction(admin=True) as c:
        c.execute("INSERT INTO sources VALUES('sec-disclosures','SEC originals','sec-public') ON CONFLICT DO NOTHING")
        item=dict(slot='annual',accession=d['accession'],form=d['form'],url=d['url'],published_at=d['published_at'],period_end='2025-09-30')
        disclosures.commit(c,iid,item,d['raw_html'],d['data'],NOW,'Authored')
        before=one(c,'SELECT data FROM performance_snapshots WHERE instrument_id=%s',(iid,))['data']
    with transaction(owner,consistent=True) as c:
        result=present(c,iid);again=present(c,iid)
        assert result==again and result['snapshot_id'] is None and result['projection_method']==amendments.METHOD
        assert result['reports']['annual']['metrics'][0]['value']=='500'
        assert result['recorded_basis']==saved_performance(c,iid)
        assert result['recorded_basis']['reports']['annual']['metrics'][0]['value'] is None
        from thesis.research.answers import filing_sources
        original_sources=filing_sources(c,iid,datetime.now(timezone.utc))
        assert original_sources
        assert all(x['performance_id']==str(result['based_on_snapshot_id']) for x in original_sources)
        assert one(c,'SELECT data FROM performance_snapshots WHERE instrument_id=%s',(iid,))['data']==before
        from thesis.research.sec.financial_depth import present as depth
        from thesis.research.sec.financial_story import present as story
        basis=depth(c,iid)['amendment_basis']
        assert story(c,iid)['amendment_basis']==basis
    with transaction(admin=True) as c:c.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-disclosures'")
    with transaction(owner,consistent=True) as c:
        assert present(c,iid)['reports']['annual']['metrics'][0]['value'] is None
        assert depth(c,iid)['amendment_basis']!=basis
        assert story(c,iid)['amendment_basis']==depth(c,iid)['amendment_basis']
    with transaction(admin=True) as c:c.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'")
    with transaction(owner,consistent=True) as c:assert present(c,iid)['status']=='unavailable'


def test_inherited_quarterly_bridge_keeps_each_inputs_original_filing_url():
    from test_financial_depth import trailing_bundle
    b=trailing_bundle();r=b['submissions']['filings']['recent']
    for v in r.values():v.append(v[-1])
    r['form'][-1]='10-Q/A';r['accessionNumber'][-1]='0000789019-26-000003'
    r['filingDate'][-1]='2026-08-01';r['acceptanceDateTime'][-1]='2026-08-01T20:00:00Z'
    d=document(b);resolver=amendments.Resolver(b,CIK,NOW,{d['accession']:d})
    from thesis.research.sec.financial_depth import trailing
    from thesis.research.sec.normalize import REVENUE
    row=trailing(b,resolver.filings,resolver.filings[-1],REVENUE,resolver)
    assert row['value']=='550'
    assert {f['accession'] for f in row['inputs']}=={'0000789019-25-000001','0000789019-26-000002'}
    for fact in row['inputs']:
        assert fact['accession'].replace('-','') in fact['filing_url']


def test_derived_evidence_retains_all_supporting_tables():
    b=amended();raw=table()+table().replace('Total revenue','Total operating income').replace('0.5','0.1').replace('0.4','0.02')
    # Supply a matching prior operating-income value in the original filing.
    income=b['companyfacts']['facts']['us-gaap']['OperatingIncomeLoss']['units']['USD']
    income.append(dict(income[0],val=20,start='2023-10-01',end='2024-09-30'))
    d=document(b,'Narrative correction only.',raw);_,_,resolver=resolved(b,d)
    result=normalize_depth(b,CIK,NOW,resolver)
    margin=next(m for m in result['trailing'] if m['key']=='operating_margin')
    assert Decimal(margin['value'])==Decimal('20')
    proofs=margin['filing_resolution']['amendments']
    assert len(proofs)==1 and len(proofs[0]['support'])==2


def test_collection_retains_chain_documents_and_reuses_older_amendments(owner):
    from thesis.research.sec.client import SourceFailure
    from thesis.service import Conflict
    b=amended();r=b['submissions']['filings']['recent'];first=r['accessionNumber'][-1]
    for v in r.values():v.append(v[-1])
    r['accessionNumber'][-1]='0000789019-25-000004';r['filingDate'][-1]='2025-11-02';r['acceptanceDateTime'][-1]='2025-11-02T20:00:00Z'
    iid=add_company('MSFT')['instrument_id'];seen=[]
    with transaction(admin=True) as c:c.execute("INSERT INTO sources VALUES('sec-disclosures','SEC originals','sec-public') ON CONFLICT DO NOTHING")
    d=document(b);older=document(b,accession=first)
    def fetch(url):
        seen.append(url)
        return older['raw_html'] if first.replace('-','') in url else d['raw_html']
    disclosures.refresh(iid,submissions=b['submissions'],fetcher=fetch)
    assert any(first.replace('-','') in url for url in seen)
    with transaction(owner,consistent=True) as c:
        assert all('_amendment_' not in x['slot'] for x in disclosures.present(c,iid)['documents'])
        assert one(c,'SELECT count(*) n FROM disclosure_documents WHERE instrument_id=%s AND accession=%s',(iid,first))['n']==1
    with pytest.raises(Conflict):disclosures.refresh(iid,submissions=b['submissions'],fetcher=lambda _:pytest.fail('Cooldown bypassed'))
    with transaction(admin=True) as c:c.execute('UPDATE disclosure_refresh_state SET last_attempt_at=NULL WHERE instrument_id=%s',(iid,))
    seen.clear();disclosures.refresh(iid,submissions=b['submissions'],fetcher=fetch)
    assert not any(first.replace('-','') in url for url in seen)
    with transaction(admin=True) as c:c.execute('UPDATE disclosure_refresh_state SET last_attempt_at=NULL WHERE instrument_id=%s',(iid,))
    seen.clear()
    def denied(url):seen.append(url);raise SourceFailure('Denied',True)
    result=disclosures.refresh(iid,submissions=b['submissions'],fetcher=denied)
    assert len(seen)==1 and result['status']=='partial'


def test_invalid_amended_borrowing_does_not_fall_back_to_older_total():
    b=amended();facts=b['companyfacts']['facts']['us-gaap']
    original=dict(facts['Assets']['units']['USD'][0],val=37)
    revised=dict(original,val=-1,accn=b['submissions']['filings']['recent']['accessionNumber'][-1],form='10-K/A',filed='2025-11-01')
    facts['DebtLongtermAndShorttermCombinedAmount']={'units':{'USD':[original,revised]}}
    _,_,resolver=resolved(b,document(b))
    result=normalize_depth(b,CIK,NOW,resolver)
    assert result['debt']['value'] is None and 'negative' in result['debt']['reason']
