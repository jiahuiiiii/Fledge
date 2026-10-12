"""Bounded, issuer-independent revenue guidance grammar over exact passages.

Never use nearby reported amounts, infer a currency/date, or borrow segment
forecasts. Arithmetic for explicit plus/minus ranges is Decimal-only.
"""
from decimal import Decimal
import re
from .performance import decimal_text

NUM = r'(?:\d{1,3}(?:,\d{3})+|\d{1,6})(?:\.\d{1,6})?'
SCALE = r'(?:billion|million|thousand|bn|[BMK])'
CURRENCY = r'(?:US\$|USD\s*|\$)'
ATOM = rf'(?P<currency>{CURRENCY})?\s*(?P<number>{NUM})\s*(?P<scale>{SCALE})?'
ATOM_RE = re.compile('^'+ATOM+'$', re.I)
ORDINAL = r'(?:first|second|third|fourth)'
PERIOD = rf'(?:(?:{ORDINAL}(?: fiscal)? quarter|full(?: fiscal)? year|fiscal year|Q[1-4])(?: (?:of )?(?:fiscal(?: year)? )?(?:20\d{{2}}))?)'
REVENUE_LABEL = r'(?:(?:(?:total|net|consolidated) )?revenues?|(?:(?:total|consolidated) )?net sales)'
HEAD = re.compile(rf'^(?:(?:Q[1-4]\s*FY\d{{2,4}}|FY\d{{2,4}})\s+)?(?:(?:{ORDINAL}(?: fiscal)? quarter|full(?: fiscal)? year|fiscal year|Q[1-4])(?: of)?(?: fiscal)?(?: year)?(?: 20\d{{2}})?\s+)?(?:(?:business|financial|current|forward-looking)\s+)?(?:outlook|guidance)(?: for (?:the )?[\w ,/–—-]+)?$', re.I)
STOP = re.compile(r'^(?:.*(?:conference call|teleconference).*|supplemental revenue information|quarterly revenue trend.*|highlights|product highlights|quarterly dividends|dividends|about .+|forward-looking statements|cautionary statement.*|safe harbor.*|.*consolidated (?:statements|balance sheets).*)$', re.I)
DATE_HEADING = re.compile(r'^(?:Three|Twelve) Months Ending (?:[A-Z][a-z]+) \d{1,2},? 20\d{2}$', re.I)
UNKNOWN = dict(metric=None,label='Company outlook',low=None,high=None,unit=None,basis=None,approximate=False)


def amount(text, inherited=None):
    m=ATOM_RE.fullmatch(text.strip())
    if not m:return None
    scale=m['scale'] or inherited
    if not scale:return None
    factor={'billion':9,'bn':9,'b':9,'million':6,'m':6,'thousand':3,'k':3}.get(scale.lower())
    if factor is None:return None
    currency=m['currency']
    return Decimal(m['number'].replace(',','')) * 10**factor, ('USD' if currency and currency.upper().startswith(('US$','USD')) else None), scale


def money_range(text, scale=None):
    text=text.strip().rstrip(';.')
    if not re.search(CURRENCY,text,re.I):return None
    approximate=bool(re.match(r'^(?:approximately|about)\s+',text,re.I))
    text=re.sub(r'^(?:approximately|about)\s+','',text,flags=re.I)
    parts=re.split(r'\s*(?:±|\+/-|plus or minus)\s*',text,flags=re.I)
    formula=None
    if len(parts)==2:
        base=amount(parts[0].rstrip(', '),scale)
        if not base:return None
        delta=re.fullmatch(rf'({NUM})\s*(?:%|percent)',parts[1],re.I)
        if delta:
            pct=Decimal(delta[1].replace(',',''))
            if pct>100:return None
            margin=base[0]*pct/100
            formula=f'{decimal_text(base[0])} ± {decimal_text(pct)}%'
        else:
            other=amount(parts[1],base[2])
            if not other or (other[1] and other[1]!=base[1]):return None
            margin=other[0];formula=f'{decimal_text(base[0])} ± {decimal_text(margin)}'
        low,high,unit=base[0]-margin,base[0]+margin,base[1]
    elif len(parts)==1:
        bounds=re.split(r'\s+(?:to|and)\s+|\s*[–—-]\s*',text,flags=re.I)
        if len(bounds)>2:return None
        last=amount(bounds[-1],scale)
        if not last:return None
        first=amount(bounds[0],last[2])
        if not first or (first[1] and last[1] and first[1]!=last[1]):return None
        low,high,unit=first[0],last[0],first[1] or last[1]
    else:return None
    if low<0 or high<low or high>Decimal('1e15'):return None
    return dict(metric='revenue',label='Revenue',low=decimal_text(low),high=decimal_text(high),unit=unit,basis=None,approximate=approximate,calculation=formula)


def first_sentence(text):
    # Whole first sentence, without splitting the decimal point. All qualifiers
    # and later sentences remain in the original forecast quotation.
    return re.split(r'(?<=[.;])\s+(?=[A-Z])',text.lstrip('•*- ').strip(),maxsplit=1)[0]


def comparison_parts(text):
    """Separate only a complete, explicit comparison from a forecast clause."""
    match=re.search(rf',\s*(?:or to grow between (?P<low>{NUM})\s*(?:%|percent) and (?P<high>{NUM})\s*(?:%|percent)\s+)?compared (?:with|to)\s+(?P<comparison>.+?)[.;]?$',text,re.I)
    if not match:return text,None
    if match['low'] and Decimal(match['low'].replace(',',''))>Decimal(match['high'].replace(',','')):return text,None
    comparison=re.fullmatch(rf'(?:(?P<amount>.+?) (?:in|for) )?(?:the )?(?P<period>{PERIOD})',match['comparison'],re.I)
    if not comparison or (comparison['amount'] and not money_range(comparison['amount'])):return text,None
    return text[:match.start()],comparison['period']


def forecast_context(text, context):
    """Omit a comparison from period detection only when it is explicitly older.

    Named quarter/year conventions must agree. Unknown, same-period or future
    comparisons keep the full context and require review.
    """
    sentence=first_sentence(text)
    forecast,comparison=comparison_parts(sentence)
    if not comparison:return sentence,False
    def order(value):
        label=value.get('period_label') or ''
        match=re.fullmatch(r'Q([1-4]) (FY)?(20\d{2})|(FY|Year )(20\d{2})',label)
        if not match or value['period_conflict']:return None
        if match[1]:return ('quarter',bool(match[2]),int(match[3]),int(match[1]))
        return ('annual',match[4]=='FY',int(match[5]),0)
    target=order(period(context+'\n'+forecast));prior=order(period(comparison))
    older=bool(target and prior and target[:2]==prior[:2] and prior[2:]<target[2:])
    return (forecast,False) if older else (sentence,True)


def prose(text, names=()):
    first=first_sentence(text)
    first=re.sub(rf'^For (?:the )?{PERIOD},\s*','',first,flags=re.I)
    first=re.sub(rf'^{PERIOD}\s+','',first,flags=re.I)
    speakers=['we','the company',*[re.escape(n) for n in names if n]]
    speaker='(?:'+'|'.join(speakers)+')'
    first=re.sub(rf'^{speaker}\s+(?:expects?|anticipates?|projects?)\s+', '',first,flags=re.I)
    first=re.sub(rf'^(?:the )?{PERIOD}\s+','',first,flags=re.I)
    growth=re.fullmatch(REVENUE_LABEL+r' (?:is expected to grow|are expected to grow|growth (?:guidance|outlook) of) (?:approximately |about )?(' + NUM + r')(?:\s*(?:to|–|-)\s*(' + NUM + r'))?\s*(?:%|percent)(?: year[- ]over[- ]year)?[.;]?',first,re.I)
    if growth:
        low=Decimal(growth[1].replace(',',''));high=Decimal((growth[2] or growth[1]).replace(',',''))
        if 0<=low<=high:return dict(metric='revenue_growth',label='Revenue growth',low=decimal_text(low),high=decimal_text(high),unit='percent',basis=None,approximate=bool(re.search('approximately|about',first,re.I)))
    first,_=comparison_parts(first)
    m=re.fullmatch(r'(?:(GAAP|non-GAAP|adjusted) )?'+REVENUE_LABEL+r'\s+(?:(?:guidance|outlook)(?:\s+(?:of|is|at)|:)\s+|(?:is |are )?(?:expected|projected|anticipated) to be\s+|to be\s+|of\s+)(?:in the range of\s+|between\s+)?(.+)',first,re.I)
    if not m:return dict(UNKNOWN)
    value=money_range(m[2])
    if value:
        value['basis']=m[1].lower() if m[1] else None
        return value
    return dict(UNKNOWN)


def period(text):
    """Literal fiscal/calendar labels only. A fiscal year never supplies a date."""
    q=[];years=[];fiscal=False
    pattern=rf'(?P<ordinal>{ORDINAL})(?: fiscal)? quarter(?: (?:of )?(?P<fiscal>fiscal(?: year)? )?(?P<year>20\d{{2}}))?|\b(?:F?Q)(?P<q>[1-4])\s*(?:[- ]?\s*(?P<fy>FY)?\s*(?P<qy>20\d{{2}}|\d{{2}}))?\b'
    for m in re.finditer(pattern,text,re.I):
        q.append(int(m['q']) if m['q'] else ['first','second','third','fourth'].index(m['ordinal'].lower())+1)
        if m['year'] or m['qy']:
            y=m['year'] or m['qy']; years.append(int(y) if len(y)==4 else 2000+int(y))
        fiscal|=bool(m['fiscal'] or m['fy'] or m[0].upper().startswith('FQ') or 'fiscal' in m[0].lower())
    if not q and re.search(r'\bthree months\b',text,re.I):q=[0]
    annual=bool(re.search(r'\b(?:full(?: fiscal)? year|fiscal year|year ending|twelve months|FY\d{2,4})\b',text,re.I)) and not q
    if annual:
        years += [int(y) for y in re.findall(r'\b(?:full(?: fiscal)? year|fiscal year)(?: (?:of )?fiscal)? (20\d{2})\b',text,re.I)]
        fy=re.findall(r'\bFY(20\d{2}|\d{2})\b',text,re.I)
        years += [int(y) if len(y)==4 else 2000+int(y) for y in fy]
        fiscal=bool(fy or re.search('fiscal',text,re.I))
    # Fiscal heading: "Fourth Quarter Fiscal Year 2026" is covered above.
    conflict=len(set(q))>1 or len(set(years))>1
    kind=('quarter' if q else 'annual' if annual else None) if not conflict else None
    year=next(iter(set(years))) if len(set(years))==1 and not conflict else None
    quarter=next(iter(set(q))) if len(set(q))==1 and not conflict else None
    label=(f'Q{quarter} '+('FY' if fiscal else '')+str(year)) if quarter and year else (('FY' if fiscal else 'Year ')+str(year)) if kind=='annual' and year else None
    return dict(period_type=kind,period_label=label,fiscal_year=year if fiscal else None,quarter=quarter,period_conflict=conflict)


def table_forecast(passages,index, prefix=()):
    """One explicit whole-company row, optionally split across adjacent lines.

    Multiple numeric columns are accepted only when identical (GAAP/non-GAAP),
    or when remaining columns are explicitly labelled percentage changes.
    Unsupported multi-period layouts are retained as excerpts, never guessed.
    """
    p=passages[index];parts=[v.strip() for v in p['quote'].split('|') if v.strip()]
    label=re.fullmatch(r'(?:(GAAP|non-GAAP) )?'+REVENUE_LABEL,parts[0],re.I) if parts else None
    if not label:return None
    evidence=[p]; values=parts[1:]
    if not values and index+1<len(passages):
        evidence.append(passages[index+1]);values=[v.strip() for v in evidence[-1]['quote'].split('|') if v.strip()]
    context='\n'.join(p['quote'] for p in [*prefix,*passages])
    if re.search(r'\b(?:segment(?:s)?|business unit|geographic|regional) (?:revenues?|net sales|guidance|outlook)\b',context,re.I):return dict(UNKNOWN,evidence=evidence)
    scales={m.lower() for m in re.findall(r'\b(?:dollars are in|in) (millions|billions|thousands)\b',context,re.I)}
    scale=next(iter(scales))[:-1] if len(scales)==1 else None
    # Original reconciliation columns: GAAP From/To, adjustment, Non-GAAP
    # From/To. Support only identical complete ranges on both bases.
    if scale and re.search(r'From\s+To\s+Adj',context.replace('|',' '),re.I):
        joined=' '.join(values)
        cells=re.fullmatch(rf'\$\s*({NUM})\s+\$\s*({NUM})\s+\$\s*—\s+\$\s*({NUM})\s+\$\s*({NUM})',joined)
        if cells and cells[1]==cells[3] and cells[2]==cells[4]:values=[f'${cells[1]} to ${cells[2]}']
    parsed=[]
    for value in values:
        if not re.search(CURRENCY,value,re.I) and re.search(r'\bdollars\b|\bUSD\b|\$\s*in ',context,re.I) and re.fullmatch(rf'{NUM}(?:\s+to\s+{NUM})?',value):value='$'+value
        v=money_range(value,scale)
        if v:parsed.append(v)
        elif re.fullmatch(r'[\d.,% ()+–—-]+(?:\s+to\s+[\d.,% ()+–—-]+)?',value) and '%' in value and re.search(r'\bChange\b',context):continue
        else:return dict(UNKNOWN,evidence=evidence)
    if not parsed or len({(v['low'],v['high'],v['unit']) for v in parsed})!=1:return dict(UNKNOWN,evidence=evidence)
    # Do not collapse two forecast periods with coincidentally equal values.
    if period(context)['period_conflict']:return dict(UNKNOWN,evidence=evidence)
    value=parsed[0]
    header='\n'.join(p['quote'] for p in [*prefix,*passages[:index]])
    if re.search(r'\bGAAP\b',header) and not re.search(r'non.GAAP',header,re.I):value['basis']='gaap'
    elif re.search(r'non.GAAP',header,re.I) and not re.search(r'(?<![-\w])GAAP',header):value['basis']='non-gaap'
    if label[1]:value['basis']=label[1].lower()
    return dict(value,evidence=evidence)
