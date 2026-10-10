"""Authored Inline XBRL controls; optional frozen original-source regression."""
from copy import deepcopy
from pathlib import Path
import os
import pytest
from thesis import service
from thesis.config import OWNER
from thesis.db import transaction, one
from thesis.research.sec import segment_revenue as segments, disclosures
from thesis.research.sec.service import add_company
from test_disclosures import HTML, metadata, disclosure_scope

CONCEPT = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
AXIS = 'us-gaap:StatementBusinessSegmentsAxis'


def context(key, member=None, *, axis=AXIS, start='2024-10-01', end='2025-09-30', cik='0000789019', extra=''):
    dimension = f'<xbrldi:explicitMember dimension="{axis}">{member}</xbrldi:explicitMember>' if member else ''
    return f'<xbrli:context id="{key}"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">{cik}</xbrli:identifier><xbrli:segment>{dimension}{extra}</xbrli:segment></xbrli:entity><xbrli:period><xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate></xbrli:period></xbrli:context>'


def fact(key, value, *, concept=CONCEPT, **attrs):
    attributes = dict(name=concept, contextRef=key, unitRef='usd', decimals='-6', scale='6', format='ixt:num-dot-decimal', id='f-'+key)
    attributes.update(attrs)
    return '<ix:nonFraction '+' '.join(f'{k}="{v}"' for k,v in attributes.items())+'>'+value+'</ix:nonFraction>'


def filing(*, total='100', members=None, axis=AXIS, more_contexts='', more_facts=''):
    members = members if members is not None else [('custom:SubscriptionsandServicesMember','60'),('custom:ProductsMember','40')]
    contexts=context('total')+''.join(context('s'+str(i),member,axis=axis) for i,(member,_) in enumerate(members))
    facts=fact('total',total)+''.join(fact('s'+str(i),value) for i,(_,value) in enumerate(members))
    prose=HTML.decode().split('<body>')[1].split('</body>')[0]
    return (f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:xbrli="{segments.XI}" xmlns:xbrldi="{segments.XD}" xmlns:ix="{segments.IX}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:iso4217="{segments.ISO}" xmlns:us-gaap="http://fasb.org/us-gaap/2025" xmlns:srt="http://fasb.org/srt/2025" xmlns:dei="http://xbrl.sec.gov/dei/2025" xmlns:custom="http://example.test/2025" xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2020-02-12"><body><ix:header><ix:resources>{contexts}{more_contexts}<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit></ix:resources><ix:hidden><ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="total">2025-09-30</ix:nonNumeric></ix:hidden></ix:header>{prose}<div>{facts}{more_facts}</div></body></html>').encode()


def read(raw=None):return segments.extract(raw or filing(),789019)


def test_exact_scale_context_and_source_evidence():
    group=read()['groups'][0]
    assert group['total']=='100000000' and group['component_sum']=='100000000' and group['chartable']
    assert {m['label']:m['percentage'] for m in group['members']}=={'Products':'40','Subscriptions and Services':'60'}
    assert group['start']=='2024-10-01' and group['end']=='2025-09-30'
    assert group['members'][0]['inputs'][0]['fact_id']=='f-s1'
    assert group['members'][0]['inputs'][0]['display']=='40'


@pytest.mark.parametrize('axis,kind',[(AXIS,'Operating segments'),('srt:ProductOrServiceAxis','Products and services'),('srt:StatementGeographicalAxis','Reported geographies')])
def test_dimensions_are_explicit_and_supported(axis,kind):
    assert read(filing(axis=axis))['groups'][0]['kind']==kind
    assert read(filing(axis='custom:StatementBusinessSegmentsAxis'))['groups']==[]


@pytest.mark.parametrize('change,reason',[
    ('nil','missing'),('unit','USD'),('transform','transformation'),('continued','structure'),
    ('precision','precision'),('conflict','conflicting'),('total','reconcile'),('zero','Zero'),('negative','negative')])
def test_unavailable_conflicting_and_nonadditive_values_never_create_mix(change,reason):
    raw=filing()
    if change=='nil':raw=raw.replace(b'id="f-s0"',b'id="f-s0" xsi:nil="true"')
    if change=='unit':raw=raw.replace(b'iso4217:USD',b'iso4217:EUR')
    if change=='transform':raw=raw.replace(b'ixt:num-dot-decimal',b'ixt:num-comma-decimal')
    if change=='continued':raw=raw.replace(b'id="f-s0"',b'id="f-s0" continuedAt="later"')
    if change=='precision':raw=raw.replace(b'decimals="-6"',b'decimals="unknown"')
    if change=='conflict':raw=filing(more_facts=fact('s0','61',id='conflicting'))
    if change=='total':raw=filing(total='101')
    if change=='zero':raw=filing(total='0',members=[('custom:ZeroMember','0')])
    if change=='negative':raw=filing(total='20').replace(b'id="f-s1"',b'id="f-s1" sign="-"')
    group=read(raw)['groups'][0]
    assert not group['chartable'] and reason in group['reason']
    assert all(m['percentage'] is None for m in group['members'])


def test_identical_duplicate_is_safe_but_duplicate_xml_ids_are_not():
    assert read(filing(more_facts=fact('s0','60',id='same-value')))['groups'][0]['chartable']
    for raw in [filing(more_facts=fact('s0','60')),filing(more_contexts=context('s0')),filing().replace(b'</ix:resources>',b'<xbrli:unit id="usd"><xbrli:measure>iso4217:EUR</xbrli:measure></xbrli:unit></ix:resources>')]:
        with pytest.raises(ValueError,match='duplicated'):read(raw)


def test_namespace_aliases_cannot_turn_conflicting_categories_into_valid_mix():
    raw=filing(members=[('custom:ProductsMember','60'),('alias:ProductsMember','40')])
    raw=raw.replace(b'xmlns:custom=',b'xmlns:alias="http://example.test/2025" xmlns:custom=')
    group=read(raw)['groups'][0]
    assert len(group['members'])==1 and not group['chartable'] and 'conflicting' in group['reason']


def test_excessive_decimal_precision_is_not_rounded_into_an_exact_value():
    raw=filing(members=[('custom:ProductsMember','0.1234567890123456789012345678901234')])
    group=read(raw)['groups'][0]
    assert group['members'][0]['value'] is None and not group['chartable']


@pytest.mark.parametrize('extra',[
    '<xbrldi:typedMember dimension="custom:OtherAxis"/>',
    '<xbrldi:explicitMember dimension="srt:StatementGeographicalAxis">custom:SomewhereMember</xbrldi:explicitMember>',
    '<custom:UnknownContextQualifier/>'])
def test_nested_typed_or_unknown_context_is_not_added(extra):
    data=read(filing(more_contexts=context('other','custom:OtherMember',extra=extra),more_facts=fact('other','50')))
    assert len(data['groups'][0]['members'])==2 and data['groups'][0]['chartable']


def test_wrong_issuer_comparatives_and_other_concepts_are_not_pooled():
    contexts=context('wrong','custom:OtherMember',cik='320193')+context('old','custom:OtherMember',start='2023-10-01',end='2024-09-30')
    raw=filing(more_contexts=contexts,more_facts=fact('wrong','50')+fact('old','50')+fact('s0','500',id='custom-revenue',concept='custom:Revenue'))
    assert read(raw)['groups'][0]['chartable']
    with pytest.raises(ValueError,match='reporting-period'):segments.extract(raw,320193)


def test_periods_and_revenue_definitions_stay_separate():
    extra=context('quarter-total',start='2025-07-01')+context('quarter-part','custom:ProductsMember',start='2025-07-01')
    raw=filing(more_contexts=extra,more_facts=fact('quarter-total','25')+fact('quarter-part','25')+fact('s0','60',concept='us-gaap:Revenues',id='other-concept'))
    groups=read(raw)['groups']
    assert len(groups)==2 and {g['total'] for g in groups}=={'100000000','25000000'}
    assert all(g['chartable'] for g in groups)
    # Same local concept in a different namespace cannot provide its denominator.
    raw=filing().replace(b'xmlns:srt=',b'xmlns:prior="http://fasb.org/us-gaap/2024" xmlns:srt=')
    raw=raw.replace((f'name="{CONCEPT}" contextRef="total"').encode(),b'name="prior:RevenueFromContractWithCustomerExcludingAssessedTax" contextRef="total"')
    assert not read(raw)['groups'][0]['chartable']


def test_excluded_display_text_and_nested_date_are_read_correctly():
    raw=filing().replace(b'>60</ix:nonFraction>',b'>6<ix:exclude>Footnote</ix:exclude>0</ix:nonFraction>')
    raw=raw.replace(b'>2025-09-30</ix:nonNumeric>',b'>September <span>30</span>, 2025</ix:nonNumeric>')
    assert read(raw)['groups'][0]['chartable']


@pytest.mark.parametrize('raw',[b'<!DOCTYPE html><html/>',b'<html>',b'<a>'*130+b'</a>'*130,b'<html xmlns:p="first"><span xmlns:p="second"/></html>'])
def test_unsupported_xml_is_visible_failure(raw):
    with pytest.raises(ValueError):read(raw)


def test_source_permission_and_workspace_read_do_not_rewrite_documents(owner):
    iid=add_company('MSFT')['instrument_id']
    disclosures.refresh(iid,submissions=metadata(),fetcher=lambda _:filing())
    with transaction(owner,consistent=True) as conn:
        before=one(conn,'SELECT md5(raw_html::text) hash FROM disclosure_documents WHERE instrument_id=%s',(iid,))
        view=segments.present(conn,iid)
        assert view['status']=='available' and view['groups'][0]['period']=='Annual'
    assert service.state(OWNER,iid)['segment_revenue']['groups'][0]['chartable']
    with transaction(admin=True) as conn:conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-disclosures'")
    try:
        with transaction(owner,consistent=True) as conn:
            assert segments.present(conn,iid)['groups']==[]
            assert one(conn,'SELECT md5(raw_html::text) hash FROM disclosure_documents WHERE instrument_id=%s',(iid,))==before
    finally:
        with transaction(admin=True) as conn:conn.execute("UPDATE sources SET entitlement='sec-public' WHERE id='sec-disclosures'")


def test_real_saved_broadcom_arithmetic_and_fact_anchor():
    folder=os.environ.get('THESIS_SEGMENT_CORPUS')
    if not folder:pytest.skip('Optional retained original filings absent')
    quarter=segments.extract((Path(folder)/'quarter.html').read_bytes(),1730168)
    operating=next(g for g in quarter['groups'] if g['kind']=='Operating segments' and g['start']=='2026-05-04')
    assert operating['total']=='29591000000' and operating['chartable']
    semis=next(m for m in operating['members'] if m['label']=='Semiconductor Solutions')
    assert semis['value']=='20839000000' and any(f['fact_id']=='f-1055' for f in semis['inputs'])
    annual=segments.extract((Path(folder)/'annual.html').read_bytes(),1730168)
    operating=next(g for g in annual['groups'] if g['kind']=='Operating segments')
    assert operating['total']=='63887000000' and operating['chartable']
    geography=[g for g in annual['groups'] if g['kind']=='Reported geographies']
    assert {g['view_label'] for g in geography}=={'Countries','Regions'}
    assert all(g['chartable'] and g['total']=='63887000000' for g in geography)
    assert sorted(len(g['members']) for g in geography)==[3,5]


def test_historical_exact_filing_is_read_without_latest_period_substitution(owner):
    from datetime import datetime, timezone
    from thesis.research.sec.disclosure_text import parse
    iid=add_company('MSFT')['instrument_id']
    raw=filing();item=disclosures.plan(metadata(),789019,datetime.now(timezone.utc))[0]
    # Retain a historical document without installing a current pointer.
    item.update(history=True,slot='revenue_history')
    with transaction(source=True) as conn:
        disclosures.commit(conn,iid,item,raw,parse(raw,form='10-K',cik=789019),datetime.now(timezone.utc),'Example')
    flow={'periods':[{'kind':'annual','metrics':[{'key':'revenue','inputs':[{'filing_url':item['url'],'start':'2024-10-01','end':'2025-09-30','concept':CONCEPT.split(':')[1]}]}]}]}
    with transaction(consistent=True) as conn:
        assert segments.present(conn,iid,flow)['groups'][0]['total']=='100000000'
        assert segments.present(conn,iid,{'periods':[]})['groups']==[]
    with transaction(admin=True) as conn:
        conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-disclosures'")
    try:
        with transaction(consistent=True) as conn:
            assert segments.present(conn,iid,flow)['groups']==[]
    finally:
        with transaction(admin=True) as conn:
            conn.execute("UPDATE sources SET entitlement='sec-public' WHERE id='sec-disclosures'")


def test_comparative_periods_are_opt_in_and_never_pooled():
    extra=context('old-total',start='2023-10-01',end='2024-09-30')+context('old-part','custom:ProductsMember',start='2023-10-01',end='2024-09-30')
    raw=filing(more_contexts=extra,more_facts=fact('old-total','25')+fact('old-part','25'))
    assert len(read(raw)['groups'])==1
    groups=segments.extract(raw,789019,True)['groups']
    assert len(groups)==2 and all(g['chartable'] for g in groups)
    assert {g['total'] for g in groups}=={'100000000','25000000'}


def bridge_fixture():
    base=read()['groups'][0]
    dates=[('2024-10-01','2025-09-30'),('2025-10-01','2026-06-30'),('2024-10-01','2025-06-30')]
    groups=[];inputs=[]
    for n,(start,end) in enumerate(dates):
        g=deepcopy(base);g.update(start=start,end=end,url=f'https://www.sec.gov/filing{n}.htm',form='10-K' if n==0 else '10-Q')
        groups.append(g)
        inputs.append(dict(value=g['total'],start=start,end=end,concept=CONCEPT.split(':')[1],filing_url=g['url']))
    p=dict(id='trailing:fixture',kind='trailing',start='2025-07-01',end='2026-06-30',metrics=[dict(key='revenue',value='100000000',inputs=inputs,calculated=True)])
    return p,groups


def test_trailing_breakdown_matches_exact_three_input_bridge_and_evidence():
    period,groups=bridge_fixture()
    result=segments.trailing_groups(period,groups)
    assert len(result)==1 and result[0]['total']=='100000000'
    assert {m['value'] for m in result[0]['members']}=={'40000000','60000000'}
    assert result[0]['period_id']==period['id'] and result[0]['revenue_inputs']==period['metrics'][0]['inputs']
    assert all(len(m['inputs'])==3 and m['calculated'] for m in result[0]['members'])
    assert all('#f-' in f['filing_url'] for m in result[0]['members'] for f in m['inputs'])


@pytest.mark.parametrize('change',['missing','overlap','member','label','total','dates','concept','negative','url'])
def test_trailing_breakdown_rejects_incomplete_or_changed_categories(change):
    p,groups=bridge_fixture()
    if change=='missing':groups.pop()
    if change=='overlap':groups[1]['chartable']=False
    if change=='member':groups[1]['members'][0]['member']='custom:NewMember'
    if change=='label':groups[1]['members'][0]['label']='Changed basis'
    if change=='total':p['metrics'][0]['value']='101000000'
    if change=='dates':p['start']='2025-07-02'
    if change=='concept':p['metrics'][0]['inputs'][1]['concept']='Revenues'
    if change=='negative':groups[2]['members'][0]['value']='1000000000'
    if change=='url':groups[1]['url']='https://www.sec.gov/other.htm'
    assert segments.trailing_groups(p,groups)==[]


def test_older_dei_quarter_namespace_keeps_exact_reporting_date():
    raw=filing().replace(b'xbrl.sec.gov/dei/2025',b'xbrl.sec.gov/dei/2021q4')
    assert read(raw)['groups'][0]['chartable']


def test_standard_operating_segments_qualifier_is_retained_and_reconciled():
    qualifier='<xbrldi:explicitMember dimension="srt:ConsolidationItemsAxis">us-gaap:OperatingSegmentsMember</xbrldi:explicitMember>'
    raw=filing().replace(b'</xbrldi:explicitMember>',('</xbrldi:explicitMember>'+qualifier).encode())
    group=read(raw)['groups'][0]
    assert group['chartable'] and group['total']=='100000000'
    assert len(group['members'][0]['inputs'][0]['dimensions'])==2
    for member in ['us-gaap:IntersegmentEliminationMember','custom:OperatingSegmentsMember']:
        assert read(raw.replace(b'us-gaap:OperatingSegmentsMember',member.encode()))['groups']==[]


def geographic_disclosures():
    axis='srt:StatementGeographicalAxis'
    members=[('custom:AmericasMember','60'),('custom:AsiaPacificMember','40')]
    extra=context('country-a','custom:FirstCountryMember',axis=axis)+context('country-b','custom:OtherCountriesMember',axis=axis)
    raw=filing(axis=axis,members=members,more_contexts=extra)
    region=fact('total','100')+fact('s0','60')+fact('s1','40')
    countries='Net revenue by country is based on delivery location. '+fact('country-a','70')+fact('country-b','30')
    return raw.replace(('<div>'+region+'</div>').encode(),('<table><tr><td>'+region+'</td></tr></table><div>'+countries+'</div>').encode())


def test_complete_country_and_region_disclosures_connect_separately():
    groups=read(geographic_disclosures())['groups']
    assert [g['view_label'] for g in groups]==['Countries','Regions']
    assert all(g['chartable'] and g['component_sum']==g['total']=='100000000' for g in groups)
    assert [set(m['value'] for m in g['members']) for g in groups]==[{'70000000','30000000'},{'60000000','40000000'}]
    assert len({g['view_id'] for g in groups})==2
    assert 'delivery location' in groups[0]['disclosure']['description']
    assert all(m['inputs'][0]['fact_id'] for g in groups for m in g['members'])


@pytest.mark.parametrize('change',['same-block','missing-total','missing-member','conflict','overlap','unlabelled-prose','hidden'])
def test_geographic_partitions_require_source_proof_and_complete_nonoverlap(change):
    raw=geographic_disclosures()
    if change=='same-block':
        region=fact('total','100')+fact('s0','60')+fact('s1','40')
        raw=raw.replace(('<table><tr><td>'+region+'</td></tr></table><div>').encode(),('<div>'+region).encode())
    if change=='missing-total':raw=raw.replace(fact('total','100').encode(),b'').replace(b'</body>',fact('total','100').encode()+b'</body>')
    if change=='missing-member':raw=raw.replace(fact('country-b','30').encode(),b'')
    if change=='conflict':raw=raw.replace(b'</body>',fact('country-a','71',id='conflicting-country').encode()+b'</body>')
    if change=='overlap':raw=raw.replace(fact('country-a','70').encode(),fact('s0','60',id='duplicate-a').encode()).replace(fact('country-b','30').encode(),fact('s1','40',id='duplicate-b').encode())
    if change=='unlabelled-prose':raw=raw.replace(b'Net revenue by country',b'Some figures')
    if change=='hidden':raw=raw.replace(b'<div>Net revenue',b'<ix:hidden><div>Net revenue').replace(b'</div></body>',b'</div></ix:hidden></body>')
    groups=read(raw)['groups']
    if change=='overlap':
        # An identical repeated full set stays one set, never two flows.
        assert len(groups)==1 and len(groups[0]['members'])==2
    else:
        assert len(groups)==1 and not groups[0]['chartable'] and 'view_id' not in groups[0]


def test_trailing_geographies_do_not_mix_country_and_region_views():
    period,groups=bridge_fixture()
    country=[];region=[]
    for group in groups:
        group.update(kind='Reported geographies',view_id='country',view_label='Countries')
        country.append(group)
        region.append(dict(deepcopy(group),view_id='region',view_label='Regions'))
    assert len(segments.trailing_groups(period,country+region))==2
    country[1]['view_id']='different-members'
    assert [g['view_id'] for g in segments.trailing_groups(period,country+region)]==['region']


def test_country_prose_follows_only_an_explicit_bounded_page_continuation():
    raw=geographic_disclosures()
    start='<div>Net revenue by country is based on delivery location. '+fact('country-a','70')
    raw=raw.replace(start.encode(),('<ix:continuation id="first" continuedAt="second">'+start+' for fiscal').encode())
    raw=raw.replace(fact('country-b','30').encode(),('</div></ix:continuation><ix:continuation id="second"><div>years '+fact('country-b','30')).encode())
    raw=raw.replace(b'</div></body>',b'</div></ix:continuation></body>')
    groups=read(raw)['groups']
    assert [g['view_label'] for g in groups]==['Countries','Regions']
    assert groups[0]['disclosure']['continuation_ids']==['second']
    for changed in [raw.replace(b'continuedAt="second"',b'continuedAt="missing"'),raw.replace(b'for fiscal',b'for fiscal.'),raw.replace(b'<div>years',b'<div>Unrelated')]:
        assert not read(changed)['groups'][0]['chartable']
