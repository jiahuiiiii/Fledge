"""Saved-close alert-rule comparison. No provider calls or app writes.

Capture uses a database-enforced read-only transaction; compare is file-only.
Experimental thresholds are explicit candidates, never live defaults.
"""
import argparse
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from thesis.monitoring import price_moves as M,us_session  # noqa:E402
from thesis.research.price_history import BASIS  # noqa:E402

POLICY='saved-close-drawdown-comparison-1'
MODES=('fixed7','scaled4_floor2','scaled4_floor7')
ZERO=Decimal(0)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))


def session(day):
    # Only the portion of2025 actually needed for these saved windows.
    # NYSE2025calendar: https://ir.theice.com/press/news-details/2024/NYSE-Group-Announces-2025-2026-and-2027-Holiday-and-Early-Closings-Calendar/default.aspx
    if day.year==2025 and day.month>=10:
        return day.weekday()<5 and day.strftime('%m-%d') not in {'11-27','12-25'}
    if day.year not in us_session.CLOSED:raise ValueError('Unsupported replay calendar; do not invent missing sessions.')
    return bool(us_session.bounds(day))


def previous_day(day):
    for offset in range(1,11):
        prior=day-timedelta(days=offset)
        if session(prior):return prior
    raise ValueError('No supported preceding trading session.')


def validated(series):
    if (series.get('basis')!=BASIS or series.get('currency')!='USD'
            or series.get('interval')!='1d' or series.get('exchange_timezone')!='America/New_York'):
        raise ValueError('Use one supported split-adjusted daily-history vintage.')
    raw=series.get('bars')
    if not isinstance(raw,list) or not 1<=len(raw)<=400:raise ValueError('A saved history must contain1–400bars.')
    result=[];seen=set();last=None
    for bar in raw:
        day=date.fromisoformat(bar['date']);price=M.positive(bar.get('close'))
        if day in seen or (last and day<=last):raise ValueError('Duplicate or unordered daily history.')
        seen.add(day);last=day
        if price is None or not session(day):raise ValueError('A close is invalid or not a trading session.')
        if bar.get('provisional') is not False:continue
        result.append(dict(date=day,close=price))
    return result


class Episodes:
    """Independent directions, pinned anchors,5-point steps, half-recovery reset."""
    def __init__(self,mode):
        if mode not in MODES:raise ValueError('Unknown episode candidate.')
        self.mode=mode;self.active={};self.rearm={}

    def threshold(self,typical):
        if self.mode=='fixed7':return Decimal(7)
        return max(Decimal(2 if self.mode=='scaled4_floor2' else 7),4*typical)

    def tick(self,window,typical):
        result=[]
        for direction in ('down','up'):
            event=self.direction_tick(direction,window,typical)
            if event:result.append(event)
        return result

    def direction_tick(self,direction,window,typical):
        current=window[-1];price=current['close'];day=current['date'];active=self.active.get(direction)
        if active:
            extreme=min(active['extreme'],price) if direction=='down' else max(active['extreme'],price)
            active['extreme']=extreme
            midpoint=(active['anchor']+extreme)/2
            recovered=price>=midpoint if direction=='down' else price<=midpoint
            if recovered:
                # Recovery cannot instantly re-enter from the same old anchor.
                self.rearm[direction]=day;self.active.pop(direction);active=None
            else:
                depth=self.depth(price,active)
                if depth>=active['next']:return self.alert(day,price,active,depth,'follow_up')
                return None
        available=[b for b in window if b['date']>=self.rearm.get(direction,date.min)]
        if not available:return None
        anchor=(max if direction=='down' else min)(available,key=lambda b:b['close'])
        anchor=[b for b in available if b['close']==anchor['close']][-1]
        threshold=self.threshold(typical)
        state=dict(direction=direction,anchor=anchor['close'],anchor_date=anchor['date'],
            extreme=price,threshold=threshold,next=threshold,typical=typical)
        depth=self.depth(price,state)
        if depth<threshold:return None
        self.active[direction]=state
        return self.alert(day,price,state,depth,'entry')

    @staticmethod
    def depth(price,state):
        return (1-price/state['anchor'])*100 if state['direction']=='down' else (price/state['anchor']-1)*100

    @staticmethod
    def alert(day,price,state,depth,kind):
        crossed=[]
        while state['next']<=depth:
            crossed.append(str(state['next']));state['next']+=5
        return dict(date=day.isoformat(),direction=state['direction'],kind=kind,close=str(price),
            anchor=str(state['anchor']),anchor_date=state['anchor_date'].isoformat(),excursion_percent=str(depth),
            threshold_percent=str(state['threshold']),typical_at_entry=str(state['typical']),
            crossed_levels=crossed,next_level=str(state['next']))


def replay(series,index=None):
    bars=validated(series);index=index or {};segment=[];states={m:Episodes(m) for m in MODES}
    days=[];gaps=0;thresholds=M.Thresholds()
    for bar in bars:
        if segment and segment[-1]['date']!=previous_day(bar['date']):
            gaps+=1;segment=[];states={m:Episodes(m) for m in MODES}
        segment.append(bar)
        # Exactly60prior daily returns, excluding today's return, need61prior closes.
        if len(segment)<62:continue
        returns=[(b['close']/a['close']-1)*100 for a,b in zip(segment[-62:-2],segment[-61:-1])]
        assert len(returns)==60
        typical=sum(map(abs,returns),ZERO)/60
        change=(bar['close']/segment[-2]['close']-1)*100
        two=(bar['close']/segment[-3]['close']-1)*100
        previous=previous_day(bar['date']).isoformat();day=bar['date'].isoformat()
        known_index=day in index and previous in index
        indexes={}
        if known_index:
            benchmark=(index[day]/index[previous]-1)*100
            indexes={'QQQ':dict(gap_points=str(change-benchmark))}
        price_reasons=M.evaluate_thresholds(change,{},dict(change_percent=str(two)),thresholds)
        full_reasons=M.evaluate_thresholds(change,indexes,dict(change_percent=str(two)),thresholds)
        events={mode:state.tick(segment[-10:],typical) for mode,state in states.items()}
        days.append(dict(date=day,daily_percent=str(change),two_session_percent=str(two),typical=str(typical),
            scaled_daily_threshold=str(max(Decimal(2),Decimal('2.5')*typical)),
            scaled_daily=abs(change)>=max(Decimal(2),Decimal('2.5')*typical),
            baseline_price=bool(price_reasons),baseline_partial=bool(full_reasons),qqq_known=known_index,
            reasons=full_reasons,episodes=events,
            active={mode:{direction:dict(anchor_date=active['anchor_date'].isoformat(),threshold=str(active['threshold']))
                          for direction,active in state.active.items()} for mode,state in states.items()}))
    return dict(completed_bars=len(bars),first=bars[0]['date'].isoformat() if bars else None,
                last=bars[-1]['date'].isoformat() if bars else None,gaps=gaps,days=days)


def summarize(result):
    days=result['days'];n=len(days);baseline={d['date'] for d in days if d['baseline_price']}
    partial={d['date'] for d in days if d['baseline_partial']}
    modes={}
    for mode in MODES:
        events=[event for d in days for event in d['episodes'][mode]]
        dates={e['date'] for e in events};union=baseline|dates
        modes[mode]=dict(episode_alerts=len(events),entries=sum(e['kind']=='entry' for e in events),
            follow_ups=sum(e['kind']=='follow_up' for e in events),additional_days=len(dates-baseline),
            combined_days=len(union),combined_per21=round(len(union)*21/n,3) if n else None,
            by_month={month:sum(day.startswith(month) for day in union) for month in sorted({d['date'][:7] for d in days})},
            train_combined=sum(d['date'] in union for d in days[:-60]),
            holdout_combined=sum(d['date'] in union for d in days[-60:]))
    return dict(completed_bars=result['completed_bars'],first=result['first'],last=result['last'],gaps=result['gaps'],
        evaluated_sessions=n,train_sessions=max(0,n-60),holdout_sessions=min(n,60),
        mean_typical=float(Decimal(sum((Decimal(d['typical']) for d in days),ZERO)/n)) if n else None,
        baseline_price_days=len(baseline),baseline_price_per21=round(len(baseline)*21/n,3) if n else None,
        baseline_partial_days=len(partial),qqq_known_sessions=sum(d['qqq_known'] for d in days),
        scaled_daily_days=sum(d['scaled_daily'] for d in days),modes=modes,
        largest_daily=sorted(days,key=lambda d:abs(Decimal(d['daily_percent'])),reverse=True)[:5],
        october_cases=[d for d in days if d['date'] in {'2026-10-14','2026-10-15'}])


def capture(output,extra_symbols=()):
    """Only minimal public-price evidence; never export account identities."""
    from thesis.db import transaction,rows
    from thesis.research.price_history import allowed
    if output.exists():raise ValueError('Choose a new frozen input path.')
    with transaction(admin=True,consistent=True) as conn:
        if not allowed(conn):raise ValueError('Saved Yahoo price access is unavailable.')
        scope=rows(conn,'SELECT count(DISTINCT owner_id) n FROM news_watches WHERE enabled')[0]['n']
        if scope>1:raise ValueError('Do not combine multiple private watchlists without an explicit account scope.')
        watched=[r['symbol'] for r in rows(conn,'SELECT DISTINCT i.symbol FROM news_watches w '
            'JOIN instruments i ON i.id=w.instrument_id WHERE w.enabled ORDER BY i.symbol')]
        symbols=sorted(set(watched)|set(extra_symbols))
        histories=rows(conn,'SELECT i.symbol,s.series,s.retrieved_at FROM instruments i '
            'LEFT JOIN price_history_state h ON h.instrument_id=i.id '
            'LEFT JOIN price_history_snapshots s ON s.id=h.current_id WHERE i.symbol=ANY(%s) ORDER BY i.symbol',(symbols,))
        refs=rows(conn,"SELECT payload,retrieved_at FROM reference_price_snapshots WHERE symbol='QQQ' AND resource='history' "
            'ORDER BY retrieved_at DESC,id DESC LIMIT 1')
        result=dict(policy=POLICY,captured_at=datetime.now(timezone.utc).isoformat(),watched=watched,
            history=[dict(symbol=h['symbol'],series=h['series'],retrieved_at=h['retrieved_at'].isoformat() if h['retrieved_at'] else None) for h in histories],
            index=refs[0]['payload'] if refs else None)
        assert conn.execute('SHOW transaction_read_only').fetchone()['transaction_read_only']=='on'
    output.write_text(json.dumps(result,indent=2)+'\n')
    return result


def compare(frozen,index_series=None):
    if frozen.get('policy')!=POLICY:raise ValueError('Use the exact frozen input contract.')
    index_series=index_series or frozen.get('index')
    if index_series and index_series.get('symbol')!='QQQ':raise ValueError('The benchmark must be an explicit QQQ history.')
    index={b['date'].isoformat():b['close'] for b in validated(index_series)} if index_series else {}
    results={};summaries={};missing=[]
    for h in frozen['history']:
        if h['symbol'] in results or h['symbol'] in missing:raise ValueError('Duplicate company histories cannot inflate counts.')
        if not h.get('series'):missing.append(h['symbol']);continue
        if h['series'].get('symbol')!=h['symbol']:raise ValueError('A saved price history belongs to another symbol.')
        value=replay(h['series'],index);results[h['symbol']]=value;summaries[h['symbol']]=summarize(value)
    return dict(policy=POLICY,mode='retrospective_saved_closes',live_changes=False,ai_calls=0,
        baseline_policy=M.POLICY,implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_sha256=hashlib.sha256(canonical(frozen).encode()).hexdigest(),watched=frozen['watched'],
        index_sessions=len(index),index_series_sha256=hashlib.sha256(canonical(index_series).encode()).hexdigest(),
        summaries=summaries,details=results,missing=missing,
        limitations=['Daily-close company-day opportunities, not intraday triggers or grouped Telegram messages.',
            'One supplied split-adjusted vintage per company; later captures are not evidence of contemporaneous availability.',
            'Baseline price-only is3%one-session/5%two-session. Full3/2/5is incomplete wherever QQQ closes are missing.',
            '60prior-return warm-up; calendar gaps reset the warm-up and episodes.',
            'Typical move is the mean absolute percent return over60prior returns; it is not standard deviation or ATR.',
            'Up/down episodes are independent. Entry thresholds freeze; fixed5percentage-point follow-ups and half-price-recovery reset.',
            'A10-session entry window still misses sufficiently slow drift; active episode anchors do not expire.',
            'The final60scored sessions are reported separately as chronological validation, not an unseen test after inspecting these results.',
            'Price frequency is not usefulness or false-positive ground truth. No best threshold is chosen automatically.'])


def markdown(report):
    lines=['# Saved-close drawdown comparison','',
        'Offline candidates only. No app setting, source refresh, model call or delivery changed.','',
        'Counts below are company-day opportunities over the same post-warm-up dates. “Per21” normalizes to21trading sessions; it is not a full-calendar-month count. QQQ coverage is partial, so baseline columns use only the stock-price3/5rules.','',
        '| Company | Scored sessions |3/5baseline days |+fixed7%: additional days |+scaled4×,2%floor: additional days |+scaled4×,7%floor: additional days |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for symbol,s in report['summaries'].items():
        modes=s['modes'];lines.append(f"|{symbol}|{s['evaluated_sessions']}|{s['baseline_price_days']}|{modes['fixed7']['additional_days']}|{modes['scaled4_floor2']['additional_days']}|{modes['scaled4_floor7']['additional_days']}|")
    lines+=['','## Frequency and coverage','',
        '|Company|First–last saved close|Mean typical daily move|Baseline per21|With fixed7per21|With scaled floor2per21|With scaled floor7per21|QQQ-paired scored sessions|',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for symbol,s in report['summaries'].items():
        m=s['modes'];typical=f"{s['mean_typical']:.2f}%" if s['mean_typical'] is not None else 'Unknown'
        lines.append(f"|{symbol}|{s['first']}–{s['last']}|{typical}|{s['baseline_price_per21']}|{m['fixed7']['combined_per21']}|{m['scaled4_floor2']['combined_per21']}|{m['scaled4_floor7']['combined_per21']}|{s['qqq_known_sessions']}|")
    lines+=['','## Limits','']+['- '+v for v in report['limitations']]
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    save=commands.add_parser('capture');save.add_argument('--output',type=Path,required=True);save.add_argument('--extra-symbols',nargs='*',default=[])
    run=commands.add_parser('compare');run.add_argument('--input',type=Path,required=True);run.add_argument('--output',type=Path,required=True)
    run.add_argument('--index-probe',type=Path)
    args=parser.parse_args()
    if args.command=='capture':
        result=capture(args.output,args.extra_symbols);print(json.dumps(dict(watched=result['watched'],histories=len(result['history']))))
    else:
        if args.output.exists():raise SystemExit('Choose a new output directory; retained evidence is not overwritten.')
        index=None
        if args.index_probe:
            from thesis.research.price_history import normalize
            probe=json.loads(args.index_probe.read_text());at=M.clock(probe.get('retrieved_at'))
            if not probe.get('usable') or at is None:raise SystemExit('Use a dated usable frozen index probe.')
            index=normalize(probe['raw'],'QQQ',at-timedelta(days=366),at,instrument_type='ETF')
        report=compare(json.loads(args.input.read_text()),index)
        if args.index_probe:report['index_input_sha256']=hashlib.sha256(args.index_probe.read_bytes()).hexdigest()
        args.output.mkdir(parents=True);(args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
        (args.output/'comparison.md').write_text(markdown(report));print(json.dumps(dict(companies=len(report['summaries']),index_sessions=report['index_sessions'],ai_calls=0)))
