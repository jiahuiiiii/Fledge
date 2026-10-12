"""General guidance layouts, negative controls and the nine retained issuers."""
import json
from pathlib import Path
from datetime import datetime, timezone
import pytest
from thesis.research.sec import guidance, guidance_formats as formats
from thesis.research.sec.disclosure_text import parse, exhibits


def read(content):
    raw=('<html><body><h1>Example Holdings quarterly financial results</h1><p>Example reports its financial results. Historical revenues were $500 million. These prior results are separate from the following dated guidance and must never supply its forecast values.</p>'+content+'</body></html>').encode()
    record=dict(company_name='Example Holdings',symbol='EXMP',published_at=datetime(2026,8,1,tzinfo=timezone.utc),data=parse(raw,form='earnings-release',cik='123'))
    return guidance.extract(record)


@pytest.mark.parametrize('text,low,high',[
    ('Revenue is expected to be $3.150 billion +/- 5%.','2992500000','3307500000'),
    ('Revenue is expected to be $108.0 billion, plus or minus 2%. The company excludes certain export sales.','105840000000','110160000000'),
    ('For the third quarter of 2026, EXMP expects revenue to be approximately $13 billion, plus or minus $300 million. The midpoint is up 41%.','12700000000','13300000000'),
    ('Example Holdings expects first quarter revenue to be in the range of $1.375 billion to $1.425 billion.','1375000000','1425000000'),
    ('Total revenue guidance of US$1,200 to US$1,350 million.','1200000000','1350000000'),
    ('We expect revenue to be between USD 1.2 and USD 1.4 billion.','1200000000','1400000000'),
])
def test_common_prose_decimal_ranges(text,low,high):
    result=formats.prose(text,['Example Holdings','EXMP'])
    assert (result['metric'],result['low'],result['high'])==('revenue',low,high)


@pytest.mark.parametrize('text',[
    'Automotive revenue is expected to be $3 billion.',
    'Another Company expects revenue to be $3 billion.',
    'Revenue guidance of at least $3 billion.',
    'Revenue guidance of $3 million to EUR4 million.',
    'Revenue is expected to be $3 billion +/- 110%.',
    'Revenue is expected to be $3 billion if a pending deal closes.',
    'Revenue was $3 billion.',
    'Revenue guidance of $3 to $2 billion.',
])
def test_do_not_relabel_segments_other_issuers_conditions_actuals_or_invalid_ranges(text):
    assert formats.prose(text,['Example Holdings'])['metric'] is None


def test_table_split_rows_duplicate_gaap_and_percent_change_columns():
    view=read('<h2>Business Outlook</h2><p>The following table presents guidance for the first quarter of fiscal 2027:</p><p>GAAP Outlook | Non-GAAP Outlook</p><p>Revenue</p><p>$61.5 billion ± $1.5 billion | $61.5 billion ± $1.5 billion</p><h2>Conference Call</h2>')
    s=view['sections'][0];f=s['forecasts'][0]
    assert s['period_label']=='Q1 FY2027' and s['period_end'] is None
    assert (f['low'],f['high'])==('60000000000','63000000000')
    assert f['quote'].startswith('Revenue\n$61.5') and len(f['evidence'])==2
    view=read('<h2>Full Year Fiscal 2027 Guidance</h2><p>GAAP | Non-GAAP</p><p>FY27 | Change</p><p>Total Revenue | $23,279 to $23,512 | 9% to 10%</p><p>Dollars are in millions, except earnings per share.</p>')
    assert view['sections'][0]['forecasts'][0]['low']=='23279000000'


@pytest.mark.parametrize('columns',[
    '$3 billion | $4 billion',
    '$3 billion | 20%', # no Change heading
    '$3 billion | EUR3 billion',
])
def test_ambiguous_table_columns_are_not_selected_by_position(columns):
    s=read(f'<h2>Business Outlook</h2><p>First quarter of fiscal 2027 guidance</p><p>Revenue | {columns}</p>')['sections'][0]
    assert s['forecasts'][0]['metric'] is None


def test_dates_from_separate_exact_range_reconciliation_and_original_evidence():
    view=read('<h2>First Quarter Fiscal 2027 Guidance</h2><p>Total Revenue | $4,294 to $4,313</p><p>Dollars are in millions.</p><h2>Conference Call</h2><p>Details.</p><p>(In millions, except per share amounts)</p><h2>Forward-Looking Guidance</h2><p>GAAP Range of Estimate | Non-GAAP Range of Estimate</p><p>From | To | Adjmts | From | To</p><p>Three Months Ending October 31, 2026</p><p>Revenue | $ | 4,294 | $ | 4,313 | $ | — | $ | 4,294 | $ | 4,313</p><h2>About Example</h2>')
    s=view['sections'][0]
    assert s['period_end']=='2026-10-31' and s['period_evidence'][0]['heading']['quote']=='Three Months Ending October 31, 2026'
    assert len(view['sections'])==1


def test_two_distinct_periods_dates_and_amounts_never_collapse():
    view=read('<h2>First Quarter Fiscal 2027 Guidance</h2><p>Revenue guidance of $3 billion.</p><h2>Second Quarter Fiscal 2027 Guidance</h2><p>Revenue guidance of $3 billion.</p>')
    assert len(view['sections'])==2
    assert {s['period_label'] for s in view['sections']}=={'Q1 FY2027','Q2 FY2027'}
    assert all(s['period_end'] is None for s in view['sections'])


def test_expired_named_missing_and_unsupported_reasons_are_distinct():
    source=dict(status='available')
    assert guidance.availability([],source)['code']=='release_missing'
    release=dict(current=True,sections=[])
    assert guidance.availability([release],source)['code']=='not_in_release'
    release['sections']=read('<h2>First Quarter Fiscal 2027 Guidance</h2><p>Revenue guidance of $3 billion.</p>')['sections']
    assert guidance.availability([release],source)['code']=='named_period'
    release['sections'][0]['period_end']='2025-10-31'
    assert guidance.availability([release],source,today='2026-10-12')['code']=='expired'
    release['sections'][0]['forecasts'][0]['metric']=None
    assert guidance.availability([release],source)['code']=='unsupported_format'
    assert guidance.availability([release],dict(status='unavailable',message='Permission withdrawn'))['code']=='source_unavailable'


def test_link_discovery_uses_exhibit_row_without_filename_or_anchor_99():
    raw=b'<html><body><p>Example Holdings announces its financial results in the attached release. See Item 2.02 and the exhibits below for the original complete statements and management outlook for the coming quarter.</p><table><tr><td>99.01</td><td><a href="results.htm">Press release</a><a href="results.htm"> dated August 1</a></td></tr></table></body></html>'
    data=parse(raw,form='8-K',cik='123')
    assert exhibits(data,'https://www.sec.gov/Archives/edgar/data/123/000000012326000001/parent.htm')==['https://www.sec.gov/Archives/edgar/data/123/000000012326000001/results.htm']
    data['exhibit_links'].append(('https://other.example/results.htm','Exhibit 99.1 Press release'))
    assert len(exhibits(data,'https://www.sec.gov/Archives/edgar/data/123/000000012326000001/parent.htm'))==1


@pytest.mark.parametrize('symbol,code,amounts',[
    ('AAPL','not_in_release',[]),('AMD','named_period',[('12700000000','13300000000')]),
    ('AVGO','available',[('34800000000','34800000000')]),('FN','expired',[('1375000000','1425000000')]),
    ('INTU','available',[('23279000000','23512000000'),('4294000000','4313000000')]),
    ('MRVL','available',[('2992500000','3307500000')]),('MU','named_period',[('60000000000','63000000000')]),
    ('NVDA','named_period',[('105840000000','110160000000')]),('QCOM','named_period',[('9700000000','10500000000')]),
])
def test_optional_nine_retained_company_releases(symbol,code,amounts):
    path=Path(__file__).resolve().parents[1]/f'.local/live-tests/management-outlook-20261012/{symbol}.json'
    if not path.exists():pytest.skip('Optional saved public release corpus')
    data=json.loads(path.read_text());releases=[]
    for doc in data['originals']:
        if doc['form']!='earnings-release':continue
        source=next(r for r in data['guidance']['releases'] if str(r['id'])==str(doc['id']))
        parsed=guidance.extract(dict(doc,company_name=source['company_name'],symbol=symbol))
        releases.append(dict(parsed,current=True))
        for section in parsed['sections']:
            for f in section['forecasts']:
                assert doc['data']['body'][f['start']:f['end']]==f['quote']
    assert guidance.availability(releases,data['source'],today='2026-10-12')['code']==code
    actual=[(f['low'],f['high']) for r in releases for s in r['sections'] for f in s['forecasts'] if f['metric']=='revenue']
    assert actual==amounts


def test_percentage_guidance_keeps_growth_separate_from_a_revenue_amount():
    s=read('<h2>Q3 FY2027 Outlook</h2><p>Revenue is expected to grow 10 to 12 percent year-over-year.</p>')['sections'][0]
    assert s['period_label']=='Q3 FY2027'
    f=s['forecasts'][0]
    assert (f['metric'],f['low'],f['high'],f['unit'])==('revenue_growth','10','12','percent')
    assert guidance.availability([dict(current=True,sections=[s])],dict(status='available'))['code']=='growth_only'


def test_same_values_for_different_named_quarters_do_not_borrow_a_date():
    content='<h2>First Quarter Fiscal 2027 Guidance</h2><p>Revenue guidance of $3 billion.</p><h2>Second Quarter Fiscal 2027 Guidance</h2><p>Revenue guidance of $3 billion.</p><h2>Forward-looking Guidance</h2><p>Three Months Ending October 31, 2026</p><p>Revenue | $3 billion</p>'
    sections=read(content)['sections']
    assert all(s['period_end'] is None for s in sections[:2])


def test_different_ranges_in_one_period_require_review():
    s=read('<h2>First Quarter Fiscal 2027 Guidance</h2><p>Revenue guidance of $3 billion.</p><p>Revenue guidance of $4 billion.</p>')['sections'][0]
    assert s['review_status']


def test_segment_table_does_not_become_total_company_revenue():
    s=read('<h2>Business Outlook</h2><p>First quarter fiscal 2027 segment revenue guidance</p><p>Revenue | $3 billion</p>')['sections'][0]
    assert s['forecasts'][0]['metric'] is None


def test_no_dollar_currency_invented_for_bare_amount_and_shared_currency_keeps_evidence():
    assert formats.prose('Revenue is expected to be 3 billion.')['metric'] is None
    s=read('<h2>FY2027 Guidance</h2><p>Dollars are in millions.</p><p>Revenue | 3,000 to 3,100</p>')['sections'][0]
    assert s['forecasts'][0]['low']=='3000000000' and s['forecasts'][0]['unit'] is None
    assert s['period_label']=='FY2027'


@pytest.mark.parametrize('label',['Net sales','Total net sales','Consolidated net sales','Revenue'])
def test_company_sales_range_with_prior_year_growth_comparison_keeps_exact_quote(label):
    quote=f'{label} are expected to be between $197.0 billion and $202.0 billion, or to grow between 9% and 12% compared with third quarter 2025. Excluding an event in both 2025 and 2026, third quarter 2026 year-over-year growth would be nearly 400 basis points higher. This guidance anticipates an unfavorable impact of approximately 80 basis points from foreign exchange rates.'
    s=read(f'<h2>Third Quarter 2026 Guidance</h2><p>•{quote}</p><p>Operating income is expected to be between $22.5 billion and $26.5 billion, compared with $17.4 billion in third quarter 2025.</p>')['sections'][0]
    f=s['forecasts'][0]
    assert (f['metric'],f['low'],f['high'],f['unit'],f['basis'])==('revenue','197000000000','202000000000',None,None)
    assert f['quote']=='•'+quote and f['evidence'][0]['quote']==f['quote']
    assert (s['period_label'],s['period_end'],s['review_status'],s['period_conflict'])==('Q3 2026',None,False,False)
    assert guidance.availability([dict(current=True,sections=[s])],dict(status='available'))['code']=='named_period'


@pytest.mark.parametrize('heading,comparison,label',[
    ('Third Quarter 2026 Guidance','$150 billion in third quarter 2025','Q3 2026'),
    ('Third Quarter 2026 Guidance','second quarter 2026','Q3 2026'),
    ('Full Fiscal Year 2027 Guidance','full fiscal year 2026','FY2027'),
])
def test_only_explicit_older_matching_comparisons_are_separate_periods(heading,comparison,label):
    s=read(f'<h2>{heading}</h2><p>Net sales are expected to be $200 billion, compared with {comparison}.</p>')['sections'][0]
    assert s['period_label']==label and not s['review_status']
    assert s['forecasts'][0]['low']==s['forecasts'][0]['high']=='200000000000'


@pytest.mark.parametrize('comparison',[
    'third quarter 2026','third quarter 2027','third fiscal quarter 2025','third quarter',
])
def test_nonprior_or_ambiguous_comparison_period_stays_withheld(comparison):
    s=read(f'<h2>Third Quarter 2026 Guidance</h2><p>Net sales are expected to be $200 billion, compared with {comparison}.</p>')['sections'][0]
    assert s['review_status']
    assert guidance.availability([dict(current=True,sections=[s])],dict(status='available'))['code']=='needs_review'


@pytest.mark.parametrize('text',[
    'Segment net sales are expected to be $200 billion.',
    'International net sales are expected to be $200 billion.',
    'Another Company expects net sales to be $200 billion.',
    'Net sales are expected to be $200 billion if a pending deal closes.',
    'Net sales are expected to be $200 billion, compared with third quarter 2025 if a pending deal closes.',
    'Net sales are expected to be $200 billion, or to grow between 12% and 9% compared with third quarter 2025.',
    'Net sales are expected to be $200 billion in third quarter 2026 and $210 billion in fourth quarter 2026.',
    'Net sales were $200 billion.',
])
def test_sales_alias_does_not_admit_segments_conditions_actuals_or_multiple_forecasts(text):
    assert formats.prose(text,['Example Holdings'])['metric'] is None


def test_net_sales_table_and_growth_only_keep_existing_amount_rules():
    s=read('<h2>Third Quarter 2026 Guidance</h2><p>Net sales | US$197 to US$202 billion</p>')['sections'][0]
    assert s['forecasts'][0]['low']=='197000000000' and s['forecasts'][0]['unit']=='USD'
    s=read('<h2>Third Quarter 2026 Guidance</h2><p>Net sales are expected to grow 9 to 12 percent year-over-year.</p>')['sections'][0]
    assert s['forecasts'][0]['metric']=='revenue_growth'
    s=read('<h2>Third Quarter 2026 Guidance</h2><p>Segment net sales guidance</p><p>Net sales | US$197 to US$202 billion</p>')['sections'][0]
    assert s['forecasts'][0]['metric'] is None


def test_optional_saved_amazon_release_preserves_original_evidence_and_unstated_fields():
    path=Path(__file__).resolve().parents[1]/'.local/live-tests/net-sales-guidance-20261012/AMZN-before.json'
    if not path.exists():pytest.skip('Optional saved public Amazon release')
    saved=json.loads(path.read_text())
    doc=next(d for d in saved['originals'] if str(d['id'])==str(saved['guidance']['releases'][0]['id']))
    view=guidance.extract(dict(doc,company_name=saved['company']['name'],symbol='AMZN'))
    s=view['sections'][0];f=s['forecasts'][0]
    assert (f['metric'],f['low'],f['high'])==('revenue','197000000000','202000000000')
    assert f['unit'] is f['basis'] is s['period_end'] is None
    assert s['period_label']=='Q3 2026' and not s['review_status']
    for p in [s['heading_evidence'],*s['passages'],*f['evidence']]:
        assert doc['data']['body'][p['start']:p['end']]==p['quote']
