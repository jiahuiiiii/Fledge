"""Deterministic offline comparisons; developer criteria are not ground truth."""
from collections import defaultdict
from pathlib import Path
import argparse
import csv
import json
from experiments.sentiment_batching.experiment import read, digest


def value(item, field):
    if field.endswith('_nonempty'):
        return bool(item.get(field.removesuffix('_nonempty')))
    if field.startswith('reporting.'):
        return item.get('reporting_basis', {}).get(field.split('.')[1])
    return item.get(field)


def compare(a, b):
    left = {i['id']:i for i in a['items']}
    right = {i['id']:i for i in b['items']}
    if left.keys() != right.keys():
        raise ValueError('Comparisons require identical complete source sets')
    fields = ['sentiment','relevance','basis','statement','topic','reporting.kind','reporting.impact']
    changed = {k:{f:[value(left[k],f),value(right[k],f)] for f in fields
                  if value(left[k],f)!=value(right[k],f)} for k in left}
    return {'sources':len(left),
            'tone_matches':sum(left[k]['sentiment']==right[k]['sentiment'] for k in left),
            'core_matches':sum(all(value(left[k],f)==value(right[k],f) for f in fields[:4]) for k in left),
            'changed':{k:v for k,v in changed.items() if v},
            'summary_equal':a['summary']==b['summary'],
            'left_summary':a['summary'],'right_summary':b['summary'],
            'coverage_equal':{(x['source_id'],x['reference_source_id'],x['relation']) for x in a['coverage_links']}==
                             {(x['source_id'],x['reference_source_id'],x['relation']) for x in b['coverage_links']}}


def score(folder):
    folder=Path(folder)
    protocol=read(folder/'protocol.json')
    criteria=read(folder/'criteria.json')
    if digest(criteria)!=protocol['criteria_hash']:
        raise ValueError('Frozen criteria changed')
    rows, item_rows, results, comparisons, interrupted=[],[],{},[],[]
    for trial in protocol['trials']:
        root=folder/'runs'/trial['name']
        if (root/'interruption.json').exists():
            interrupted.append({'trial':trial['name'],**read(root/'interruption.json')})
            continue
        if not (root/'metrics.json').exists():continue
        metrics=read(root/'metrics.json')
        complete=(root/'result.json').exists()
        row={**{k:trial[k] for k in ('name','cohort','arm','replicate')},'complete':complete,
             'requests':len(metrics),'completed_responses':sum(m['status']=='completed' for m in metrics),
             'cost_usd':sum(m['cost_usd'] for m in metrics),'seconds':sum(m['seconds'] for m in metrics),
             'uncached_cost_usd':sum((m['input_tokens']*2500+m['output_tokens']*15000)/1_000_000_000 for m in metrics),
             'input_tokens':sum(m['input_tokens'] for m in metrics),
             'cached_tokens':sum(m['cached_tokens'] for m in metrics),
             'output_tokens':sum(m['output_tokens'] for m in metrics),
             'strict_match':0,'strict_n':0,'acceptable_match':0,'acceptable_n':0,
             'field_match':0,'field_n':0,'link_match':0,'link_n':0}
        if not complete:
            row['failure']=read(root/'failure.json')['error']
        else:
            result=read(root/'result.json');results[trial['name']]=result
            labels={s['id']:s['label'] for s in read(folder/(trial['cohort']+'-packet.json'))['sources']}
            links=[{'item':labels.get(l['source_id'],l['source_id']),
                    'reference':labels.get(l['reference_source_id'],l['reference_source_id']),
                    'relation':l['relation']} for l in result['coverage_links']]
            for item in result['items']:
                expected=criteria['cohorts'][trial['cohort']][item['id']]
                group='strict' if expected['strict'] else 'acceptable'
                row[group+'_n']+=1;row[group+'_match']+=item['sentiment'] in expected['tones']
                item_rows.append({'trial':trial['name'],'cohort':trial['cohort'],'arm':trial['arm'],
                                  'replicate':trial['replicate'],'source':item['id'],'tone':item['sentiment'],
                                  'relevance':item['relevance'],'basis':item['basis'],'statement':item['statement'],
                                  'strict':expected['strict'],'accepted':item['sentiment'] in expected['tones'],
                                  'allowed':'|'.join(expected['tones'])})
                if trial['cohort']=='CONTROL':
                    for field,allowed in criteria['control_fields'].get(item['id'],{}).items():
                        row['field_n']+=1;row['field_match']+=value(item,field) in allowed
            if trial['cohort']=='CONTROL':
                for expected in criteria['control_links']:
                    row['link_n']+=1
                    row['link_match']+=any(l['item']==expected['item'] and l['reference'] in expected['references']
                                           and l['relation']==expected['relation'] for l in links)
            row['summary']=result['summary']
        rows.append(row)
    for trial in protocol['trials']:
        name=trial['name']
        if name not in results:continue
        base=f"{trial['cohort']}-full-r{trial['replicate']}"
        if trial['arm']!='full' and base in results:
            comparisons.append({'type':'paired_arms','left':base,'right':name,**compare(results[base],results[name])})
        if trial['arm']=='batch8':
            base=f"{trial['cohort']}-batch4-r{trial['replicate']}"
            if base in results:
                comparisons.append({'type':'batch_sizes','left':base,'right':name,**compare(results[base],results[name])})
        if trial['replicate']==2:
            base=f"{trial['cohort']}-{trial['arm']}-r1"
            if base in results:
                comparisons.append({'type':'repeat_stability','left':base,'right':name,**compare(results[base],results[name])})
    report={'trials':rows,'comparisons':comparisons,'completed_trials':len(rows),
            'planned_trials':len(protocol['trials']),
            'interrupted_trials':interrupted,
            'not_started_trials':[t['name'] for t in protocol['trials']
                                  if t['name'] not in {r['name'] for r in rows}
                                  and t['name'] not in {r['trial'] for r in interrupted}],
            'cost_usd':sum(r['cost_usd'] for r in rows),
            'limits':protocol['limits']}
    (folder/'scores.json').write_text(json.dumps(report,indent=2))
    if item_rows:
        with (folder/'items.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(item_rows[0]));writer.writeheader();writer.writerows(item_rows)
    print(json.dumps([{k:r[k] for k in ('name','complete','cost_usd','seconds','strict_match','strict_n','acceptable_match','acceptable_n','field_match','field_n','link_match','link_n')} for r in rows],indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--folder',required=True)
    score(parser.parse_args().folder)
