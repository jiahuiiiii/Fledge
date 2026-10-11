"""Explicit segment reconciliations and qualified geography disclosures.

Different revenue tags may participate only in a company's own complete,
reconciled table structure. Never search for a subset that happens to add up.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, localcontext
import re

from .normalize import REVENUE
from .performance import decimal_text
from .filing_facts import read, summed
from .segment_revenue import qname, taxonomy, category, COUNTRY_NAMES


def standard_dimension(pair, namespaces, axis, member=None):
    a,m=pair
    name=qname(a,namespaces); value=qname(m,namespaces)
    return ((taxonomy(name,'srt') or taxonomy(name,'us-gaap')) and name[1]==axis and
            (member is None or (taxonomy(value,'us-gaap') and value[1]==member)))


def make_group(start,end,concept,kind,axis,members,total,proof):
    with localcontext() as ctx:
        ctx.prec=110
        sum_value=sum((Decimal(m['value']) for m in members),Decimal(0))
    if sum_value!=Decimal(total['value']): return None
    reason=None if sum_value>0 and all(Decimal(m['value'])>=0 for m in members) else 'Negative reported adjustments are listed separately; a percentage flow is unavailable.'
    for m in members:
        m.update(reason=None,percentage=decimal_text(Decimal(m['value'])/sum_value*100) if not reason else None)
    return dict(start=start,end=end,duration_days=(date.fromisoformat(end)-date.fromisoformat(start)).days+1,
                concept=concept,axis=axis,kind=kind,members=members,total=total['value'],total_inputs=[total],
                component_sum=decimal_text(sum_value),chartable=not reason,reason=reason,reconciliation=proof)


def extract(raw,cik):
    parsed=read(raw,cik);ns=parsed['namespaces'];groups=[]
    def revenue(f):return f['standard'] and f['concept'].split(':')[-1] in REVENUE and f['start'] and not f['reason'] and f['value'] is not None
    # Segment statement: every reported segment's revenue, possibly using a
    # different standard tag from the consolidated total. Duplicate conflicting
    # occurrences anywhere in the filing still disqualify the candidate.
    segment_sets=[]
    for table in parsed['tables']:
        facts=[f for row in table['rows'] for f in row['facts'] if revenue(f)]
        for start,end in {(f['start'],f['end']) for f in facts}:
            parts={}
            for f in facts:
                if (f['start'],f['end'])!=(start,end):continue
                dims=[d for d in f['dimensions'] if not standard_dimension(d,ns,'ConsolidationItemsAxis','OperatingSegmentsMember')]
                if len(dims)!=1 or category(qname(dims[0][0],ns))!='Operating segments':continue
                parts.setdefault(dims[0][1],[]).append(f)
            if len(parts)<2:continue
            if any(len({f['value'] for f in fs})!=1 for fs in parts.values()):continue
            members=[]
            for member,fs in parts.items():
                # Keep the qualified original facts. Any same-dimensional
                # conflict, missing or unsupported value blocks recovery.
                originals=[f for f in parsed['facts'] if f['standard'] and f['concept'].split(':')[-1] in REVENUE and
                           (f['start'],f['end'])==(start,end) and sorted(f['dimensions'])==sorted(fs[0]['dimensions'])]
                if any(f['reason'] or f['value']!=fs[0]['value'] for f in originals):break
                label=re.sub(r'Member$','',member.split(':')[-1])
                members.append(dict(member=member,label=label.upper() if len(label)<=4 else re.sub(r'(?<=[a-z])(?=[A-Z])',' ',label),value=fs[0]['value'],inputs=deepcopy(fs)))
            else:segment_sets.append((start,end,members))
    for table in parsed['tables']:
        all_facts=[f for row in table['rows'] for f in row['facts']]
        for start,end in {(f['start'],f['end']) for f in all_facts if revenue(f)}:
            facts=[f for f in all_facts if (f['start'],f['end'])==(start,end) and f['standard'] and f['concept'].split(':')[-1] in REVENUE]
            # The same reconciling revenue is sometimes repeated in the profit
            # reconciliation. Retain its evidence, count its exact context once.
            distinct={}
            for f in facts:
                key=(f['concept'],tuple(sorted(map(tuple,f['dimensions']))))
                distinct.setdefault(key,[]).append(f)
            if any(any(f['reason'] for f in fs) or len({f['value'] for f in fs})!=1 for fs in distinct.values()):continue
            facts=[fs[0] for fs in distinct.values()]
            totals=[f for f in facts if not f['dimensions']]
            subtotal=[f for f in facts if len(f['dimensions'])==1 and standard_dimension(f['dimensions'][0],ns,'ConsolidationItemsAxis','OperatingSegmentsMember')]
            adjustments=[f for f in facts if any(standard_dimension(d,ns,'ConsolidationItemsAxis','MaterialReconcilingItemsMember') for d in f['dimensions'])]
            if len(totals)==1 and len(subtotal)==1 and adjustments and len(facts)==len(adjustments)+2 and summed([subtotal[0]]+adjustments)==totals[0]['value']:
                candidates=[ms for s,e,ms in segment_sets if (s,e)==(start,end) and summed([dict(m,start=s,end=e,unit='USD',reason=None) for m in ms])==subtotal[0]['value']]
                signatures={tuple(sorted((m['member'],m['value']) for m in ms)) for ms in candidates}
                if len(signatures)==1:
                    members=deepcopy(candidates[0])
                    for f in adjustments:
                        members.append(dict(member='|'.join(sorted(m for _,m in f['dimensions'])),label=f['row_label'],value=f['value'],inputs=[deepcopy(f)]))
                    g=make_group(start,end,totals[0]['concept'],'Operating segments','us-gaap:StatementBusinessSegmentsAxis',members,deepcopy(totals[0]),
                                 dict(method='explicit-segment-reconciliation',subtotal=deepcopy(subtotal[0]),adjustments=deepcopy(adjustments)))
                    if g:groups.append(g)
            # Standard concentration-risk qualifiers describe the geographical
            # disclosure; they are not additional countries or revenue streams.
            geographic=[]
            for f in facts:
                if len(f['dimensions'])!=3:continue
                dims=[d for d in f['dimensions'] if not
                      (standard_dimension(d,ns,'ConcentrationRiskByTypeAxis','GeographicConcentrationRiskMember') or
                       standard_dimension(d,ns,'ConcentrationRiskByBenchmarkAxis','RevenueFromContractWithCustomerMember'))]
                if len(dims)==1 and category(qname(dims[0][0],ns))=='Reported geographies':geographic.append((dims[0],f))
            if len(totals)!=1 or len(geographic)<2 or len(facts)!=len(geographic)+1:continue
            if len({d[1] for d,_ in geographic})!=len(geographic) or summed([f for _,f in geographic])!=totals[0]['value']:continue
            expected={tuple(sorted(map(tuple,f['dimensions']))):f['value'] for _,f in geographic}
            all_geo=[f for f in parsed['facts'] if (f['start'],f['end'])==(start,end) and f['standard'] and f['concept'].split(':')[-1] in REVENUE and
                     any(category(qname(a,ns))=='Reported geographies' for a,_ in f['dimensions'])]
            if any(f['reason'] or expected.get(tuple(sorted(map(tuple,f['dimensions']))))!=f['value'] for f in all_geo):continue
            members=[dict(member=d[1],label=f['row_label'],value=f['value'],inputs=[deepcopy(f)]) for d,f in geographic]
            g=make_group(start,end,totals[0]['concept'],'Reported geographies',geographic[0][0][0],members,deepcopy(totals[0]),dict(method='qualified-geography-table'))
            if g:
                g.update(view_label='Countries',view_id='qualified-country-table')
                groups.append(g)
    unique={}
    for g in groups:
        key=(g['start'],g['end'],g['kind'],g['concept'])
        unique.setdefault(key,[]).append(g)
    return [values[0] for values in unique.values() if len({tuple(sorted((m['member'],m['value']) for m in g['members'])) for g in values})==1]
