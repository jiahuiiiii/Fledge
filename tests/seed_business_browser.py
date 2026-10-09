"""Whole authored documents and provider replies in a guarded disposable DB."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA,OWNER
assert str(DATA).startswith('/private/tmp/thesis-browser-')
from thesis.research.sec.service import add_company,commit_bundle
from thesis.db import transaction
from thesis.research.sec import disclosures
from thesis.research import business,fmp
from thesis.research import analyst_targets
from test_public_forecasts import page as forecast_page
from datetime import datetime,timezone
from test_disclosures import HTML,metadata
from test_segment_revenue import filing as revenue_filing, context as revenue_context, fact as revenue_fact
from test_business import response
from test_fmp import estimate,profile
from test_sec_fundamentals import bundle
iid=add_company('MSFT')['instrument_id']
# Synthetic software fixtures, never actual MSFT financial results.
fixture=bundle(annual=True,revenue=64_000_000_000,prior=52_000_000_000,income=25_000_000_000)
from copy import deepcopy
gaap=fixture['companyfacts']['facts']['us-gaap']
current=deepcopy(gaap['OperatingIncomeLoss']['units']['USD'][0])
for concept,value in [('NetCashProvidedByUsedInOperatingActivities',45_000_000_000),('PaymentsToAcquirePropertyPlantAndEquipment',5_000_000_000),('NetIncomeLoss',20_000_000_000),('DebtLongtermAndShorttermCombinedAmount',68_000_000_000),('Assets',200_000_000_000),('Liabilities',90_000_000_000),('CashAndCashEquivalentsAtCarryingValue',30_000_000_000)]:
    fact=dict(current,val=value)
    if concept in ('DebtLongtermAndShorttermCombinedAmount','Assets','Liabilities','CashAndCashEquivalentsAtCarryingValue'):fact.pop('start')
    gaap[concept]={'units':{'USD':[fact]}}
revenue=next(iter(gaap))
for concept,value in [('GrossProfit',40_000_000_000),('CostOfRevenue',24_000_000_000),('OperatingExpenses',15_000_000_000),('ProfitLoss',20_000_000_000),('ResearchAndDevelopmentExpense',8_000_000_000),('SellingGeneralAndAdministrativeExpense',5_000_000_000)]:
    gaap[concept]={'units':{'USD':[dict(current,val=value)]}}
recent=fixture['submissions']['filings']['recent']
for year,value in [(2021,27_000_000_000),(2022,33_000_000_000),(2023,36_000_000_000),(2024,52_000_000_000)]:
    accession=f'0000789019-{str(year)[2:]}-000001'
    values=dict(accessionNumber=accession,form='10-K',filingDate=f'{year}-10-30',reportDate=f'{year}-09-30',acceptanceDateTime=f'{year}-10-30T20:00:00Z',primaryDocument=f'authored-{year}.htm')
    for key,value_ in values.items():recent[key].append(value_)
    gaap[revenue]['units']['USD'].append(dict(current,val=value,start=f'{year-1}-10-01',end=f'{year}-09-30',accn=accession,filed=f'{year}-10-30',fy=year))
with transaction(source=True) as conn:commit_bundle(conn,iid,fixture,datetime.now(timezone.utc))
segment_contexts='';segment_facts=''
for key,member,value,axis,start in [
    ('qtotal',None,'16000','us-gaap:StatementBusinessSegmentsAxis','2025-07-01'),
    ('qservices','custom:SubscriptionsandServicesMember','10000','us-gaap:StatementBusinessSegmentsAxis','2025-07-01'),
    ('qproducts','custom:ProductsMember','6000','us-gaap:StatementBusinessSegmentsAxis','2025-07-01'),
    ('software','custom:SoftwareMember','56000','srt:ProductOrServiceAxis','2024-10-01'),
    ('hardware','custom:HardwareMember','8000','srt:ProductOrServiceAxis','2024-10-01'),
    ('region','custom:RegionMember','50000','srt:StatementGeographicalAxis','2024-10-01'),
    ('country','custom:CountryWithinRegionMember','30000','srt:StatementGeographicalAxis','2024-10-01'),
]:
    segment_contexts+=revenue_context(key,member,axis=axis,start=start)
    segment_facts+=revenue_fact(key,value)
segment_html=revenue_filing(total='64000',members=[('custom:SubscriptionsandServicesMember','38400'),('custom:ProductsMember','25600')],more_contexts=segment_contexts,more_facts=segment_facts)
disclosures.refresh(iid,submissions=metadata(),fetcher=lambda _:segment_html)
business.generate(iid,transport=response,owner=OWNER)
for dataset,payload in [('profile',profile()),('peers',[dict(symbol='NVDA',companyName='NVIDIA',mktCap=100)]),('estimates',estimate()),('ratios',[dict(symbol='MSFT',priceToEarningsRatioTTM=30,priceToSalesRatioTTM=5)])]:fmp.refresh(dataset,'MSFT',fetcher=lambda *_,payload=payload:payload)
analyst_targets.refresh(iid,lambda _:forecast_page(),purpose='financials')
from test_management_outlook import seed_release, release_html
with transaction(source=True) as conn:
    older_outlook=release_html(revenue='Fourth quarter GAAP revenue guidance of approximately US$62 to US$65 billion;').replace(b'Fourth Quarter',b'Full Year').replace(b'Fourth quarter',b'Full year').replace(b'fourth quarter',b'full year')
    seed_release(conn, iid, older_outlook)
    new_outlook=release_html(revenue='Fourth quarter revenue guidance of approximately $34.8 billion;', end='November 1, 2026').replace(b'2025',b'2026').replace(b'June 30, 2026',b'September 2, 2026')
    seed_release(conn, iid, new_outlook,
                 accession='0000789019-26-000090', published=datetime(2026, 9, 2, 20, tzinfo=timezone.utc), available=datetime(2026, 9, 3, tzinfo=timezone.utc))
from thesis.research import multiples
peer_id=add_company('NVDA')['instrument_id']
for company_id,symbol,pe,ps in [(iid,'MSFT',29.375,9),(peer_id,'NVDA',45.125,16)]:
    multiples.refresh(company_id,fetcher=lambda *_,symbol=symbol,pe=pe,ps=ps:dict(symbol=symbol,metric=dict(peTTM=pe,psTTM=ps)))
peer_bundle=bundle(annual=True,accession='0001045810-25-000001',revenue=80_000_000_000,prior=60_000_000_000,income=16_000_000_000)
peer_bundle['companyfacts']['cik']=1045810
peer_bundle['submissions']['cik']='0001045810'
peer_gaap=peer_bundle['companyfacts']['facts']['us-gaap']
peer_current=deepcopy(peer_gaap['OperatingIncomeLoss']['units']['USD'][0])
for concept,value in [('NetCashProvidedByUsedInOperatingActivities',8_000_000_000),('PaymentsToAcquirePropertyPlantAndEquipment',14_000_000_000),('DebtLongtermAndShorttermCombinedAmount',18_000_000_000)]:
    fact=dict(peer_current,val=value)
    if concept=='DebtLongtermAndShorttermCombinedAmount':fact.pop('start')
    peer_gaap[concept]={'units':{'USD':[fact]}}
with transaction(source=True) as conn:commit_bundle(conn,peer_id,peer_bundle,datetime.now(timezone.utc))
fmp.refresh('profile','NVDA',fetcher=lambda *_:[dict(profile('NVDA','1045810')[0],industry='Authored semiconductor business')])
fmp.refresh('ratios','NVDA',fetcher=lambda *_:[dict(symbol='NVDA',priceToEarningsRatioTTM=50,priceToSalesRatioTTM=7)])
print('Authored business/source/provider browser fixture ready; no external calls.')
