"""Offline retrospective close replay. Never calls a provider or writes app data.

ETF closes captured later are not quotes known at the original trigger time.
This checks arithmetic/group membership, not live timeliness or causal accuracy.
"""
import argparse
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from thesis.monitoring import price_moves as M  # noqa: E402
from thesis.research import price_history  # noqa: E402
from thesis.providers.ledger import canonical  # noqa: E402


def replay(prices,index,headlines,*,symbols):
    captured=M.clock(index.get('retrieved_at'))
    if captured is None or not index.get('usable'):
        raise ValueError('A dated, usable frozen ETF response is required.')
    series=price_history.normalize(index['raw'],'QQQ',captured-timedelta(days=8),captured,instrument_type='ETF')
    bars={b['date']:b for b in series['bars'] if b['provisional'] is False}
    vintage=hashlib.sha256(canonical(index).encode()).hexdigest()
    histories={h['symbol']:dict(h['series'],retrieved_at=h['retrieved_at'],
        snapshot_id='frozen-history:'+hashlib.sha256(canonical(h).encode()).hexdigest()) for h in prices['history']}
    thresholds=M.Thresholds();sessions={}
    for item in prices['quotes']:
        if item['symbol'] not in symbols or not '2026-10-13'<=item['session']<='2026-10-17':continue
        quote=item['quote'];at=M.clock(quote.get('quoted_at'))
        if at is None:continue
        current=M.checked_quote(quote,at)
        if not current or current['session'].isoformat()!=item['session']:continue
        day=item['session'];prior=M.prior_sessions(current['session'])
        indexes={}
        if prior and day in bars and prior[0].isoformat() in bars:
            change=(Decimal(bars[day]['close'])/Decimal(bars[prior[0].isoformat()]['close'])-1)*100
            indexes['QQQ']=dict(change_percent=str(change),gap_points=str(current['change']-change),
                quoted_at=None,quote_id=None,daily_snapshot_sha256=vintage,
                context='Retrospective daily close; original quote time unknown')
        two=M.two_session_move(current,histories.get(item['symbol']),captured)
        reasons=M.evaluate_thresholds(current['change'],indexes,two,thresholds)
        value=dict(policy=M.POLICY,symbol=item['symbol'],session=day,quoted_at=at.isoformat(),
            price=str(current['price']),previous_close=str(current['previous']),change_percent=str(current['change']),
            direction='up' if current['change']>0 else 'down' if current['change']<0 else 'flat',
            indexes=indexes,sector=None,two_sessions=two,reasons=reasons,triggered=bool(reasons),
            thresholds=thresholds.record(),quote_id=None,timing_eligible=False,
            quote_saved_at=item['retrieved_at'])
        sessions.setdefault(day,[]).append(value)
    result=[]
    for day,values in sorted(sessions.items()):
        events=M.group(values)
        for event in events:
            cutoff=max(M.clock(m['quoted_at']) for m in event['members'])
            relevant=[h for h in headlines if h.get('symbol') in {m['symbol'] for m in event['members']}|{'WORLD'}
                and cutoff-timedelta(days=1)<=M.clock(h['published_at'])<=cutoff]
            relevant.sort(key=lambda h:(h['published_at'],str(h.get('id',''))),reverse=True)
            event['saved_headlines']=relevant[:28]
            event['headlines_saved_after_move']=sum(M.clock(h['available_at'])>cutoff for h in relevant[:28])
            event['explanation']='Not model-tested in this replay.'
        result.append(dict(session=day,measures=values,events=events))
    covered={m['symbol'] for s in result if s['session']=='2026-10-14' for e in s['events'] for m in e['members']}
    day15=next((s for s in result if s['session']=='2026-10-15'),None)
    return dict(policy=M.POLICY,mode='retrospective_close_arithmetic',timing_verified=False,
        symbols=sorted(symbols),thresholds=thresholds.record(),sessions=result,
        october14_required_members_covered={'NVDA','AMZN','GOOGL'}<=covered,
        october15_event_count=len(day15['events']) if day15 else None,
        limitations=[
            'Later-captured ETF daily closes and saved company quotes are retrospective context, not contemporaneous ETF quotes.',
            'Headline availability is retained; a headline saved after the move cannot establish live coverage at that time.',
            'No app alerts, Telegram messages or model calls are created; semantic explanation quality and delivery delay are unverified.',
            'Market-context members need not cross a threshold; their individual qualification remains explicit.',
        ])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('prices','index','headlines','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--symbols',nargs='+',default=['NVDA','AMZN','GOOGL','AVGO','META'])
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Choose a new output path; retained replay evidence is not overwritten.')
    result=replay(*(json.loads(getattr(args,k).read_text()) for k in ('prices','index','headlines')),symbols=set(args.symbols))
    result['input_sha256']={k:hashlib.sha256(getattr(args,k).read_bytes()).hexdigest() for k in ('prices','index','headlines')}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(sessions=len(result['sessions']),events=sum(len(s['events']) for s in result['sessions']),
        october14_required_members_covered=result['october14_required_members_covered'],
        october15_event_count=result['october15_event_count'],timing_verified=False)))
