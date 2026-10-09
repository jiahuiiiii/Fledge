"""Authored financial histories in a guarded disposable database only."""
import runpy
from datetime import datetime, timezone
from thesis.config import DATA
assert str(DATA).startswith('/private/tmp/thesis-browser-')
values = runpy.run_path('tests/seed_business_browser.py')
fixture, iid = values['fixture'], values['iid']
facts = fixture['companyfacts']['facts']['us-gaap']
recent = fixture['submissions']['filings']['recent']
from thesis.db import transaction
from thesis.research.sec.service import commit_bundle

for index, year in enumerate(range(2021, 2026)):
    accession = f'0000789019-{str(year)[2:]}-000001'
    base = dict(accn=accession, form='10-K', filed=f'{year}-10-30', start=f'{year-1}-10-01', end=f'{year}-09-30')
    for concept, amount in [
        ('OperatingIncomeLoss', [8,10,12,16,25][index]),
        ('ProfitLoss', [5,7,-3,14,20][index]),
        ('NetCashProvidedByUsedInOperatingActivities', [9,12,11,24,45][index]),
        ('PaymentsToAcquirePropertyPlantAndEquipment', [2,3,4,4,5][index]),
        ('InterestExpenseNonOperating', [2,2,3,3,4][index]),
    ]:
        rows = facts.setdefault(concept, {'units': {'USD': []}})['units']['USD']
        rows[:] = [row for row in rows if row['accn'] != accession]
        rows.append(dict(base, val=amount * 1_000_000_000))
    for concept, amount in [
        ('Assets', [85,110,130,170,200][index]), ('Liabilities', [55,62,80,90,90][index]),
        ('AssetsCurrent', [23,28,31,45,60][index]), ('LiabilitiesCurrent', [15,18,20,25,30][index]),
        ('DebtLongtermAndShorttermCombinedAmount', [40,45,60,72,68][index]),
        ('CashAndCashEquivalentsAtCarryingValue', [8,10,12,22,30][index]),
        ('AccountsReceivableNetCurrent', 15), ('InventoryNet', 5), ('PropertyPlantAndEquipmentNet', 10),
        ('Goodwill', [20,25,35,50,50][index]), ('FiniteLivedIntangibleAssetsNet', 40), ('AccountsPayableCurrent', 8),
    ]:
        row = dict(base, val=amount * 1_000_000_000); row.pop('start')
        rows = facts.setdefault(concept, {'units': {'USD': []}})['units']['USD']
        rows[:] = [existing for existing in rows if existing['accn'] != accession]
        rows.append(row)
with transaction(source=True) as conn: commit_bundle(conn, iid, fixture, datetime.now(timezone.utc))
print('Financials: authored history, including a loss and changing borrowing; no external calls.')
