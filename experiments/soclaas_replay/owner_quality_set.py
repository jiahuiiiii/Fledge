"""Freeze a blind 50-source owner review; export and score entirely offline.

The export reads permitted saved research in a read-only transaction. It never
collects sources, invokes AI or writes app research. Human answers stay in the
reviewer's browser until explicitly downloaded. No AI answers are in the page.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

POLICY = 'owner-quality-set-1'
SEED = 'fledge-owner-blind-50-v1'
RELEVANCE = {'relevant', 'unrelated', 'unclear'}
TONES = {'positive', 'negative', 'mixed', 'neutral', 'unclear'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def case_evidence(packet,source):
    """The exact blind projection, shared by export and later input validation."""
    from thesis.research import reddit_thread_context
    context=[]
    if source.get('conversation'):
        context.append(dict(label='Saved parent context',passages=source['conversation']['passages']))
    for thread in reddit_thread_context.wire(packet,[source],extras=False):
        for message in thread['messages']:
            if message.get('source_label')==source['label']:continue
            context.append(dict(label='Saved discussion context · '+message['role'],passages=message['passages']))
    return dict(company=packet['company']['symbol'],company_name=packet['company']['name'],
        source_id=source['id'],channel=source['channel'],platform=source.get('platform'),title=source['title'],
        passages=source['passages'],context=context,published_at=source['published_at'],
        omitted_fragments=source.get('omitted_fragment_count',0))


def build(packets):
    """Deterministic, balanced company/channel strata, with no model labels."""
    strata = defaultdict(dict)
    for packet in packets:
        company = packet['company']
        for source in packet['sources']:
            case = case_evidence(packet,source)
            strata[(company['symbol'], source['channel'])][source['id']] = case
    if len(strata) < 2:
        raise ValueError('Use at least two populated company/channel strata.')
    selected = []
    for index, key in enumerate(sorted(strata)):
        quota = 50//len(strata) + (index < 50 % len(strata))
        values = sorted(strata[key].values(), key=lambda c: digest([SEED, c['source_id']]))
        if len(values) < quota:
            raise ValueError('Insufficient permitted sources for the fixed balanced sample.')
        selected.extend(values[:quota])
    selected.sort(key=lambda c: digest([SEED, c['company'], c['source_id']]))
    cases = [dict(case, id=f'case-{index+1:02d}') for index, case in enumerate(selected)]
    return dict(policy=POLICY, seed=SEED, created_at=datetime.now(timezone.utc).isoformat(),
                count=50, cases=cases, fingerprint=digest(cases), ai_suggestions=False,
                sampling='Balanced company/channel strata; deterministic hashes; no label selection.')


def validate_manifest(manifest):
    cases = manifest.get('cases', [])
    if (manifest.get('policy') != POLICY or manifest.get('ai_suggestions') is not False
            or len(cases) != 50 or len({c['id'] for c in cases}) != 50
            or digest(cases) != manifest.get('fingerprint')):
        raise ValueError('The fixed blind 50-source manifest changed.')


def score(manifest, labels, predictions):
    validate_manifest(manifest)
    if set(predictions)=={'fingerprint','predictions'}:
        if predictions['fingerprint']!=manifest['fingerprint']:
            raise ValueError('Predictions belong to a different frozen review sample.')
        predictions=predictions['predictions']
    ids = {case['id'] for case in manifest['cases']}
    if (labels.get('fingerprint') != manifest['fingerprint']
            or labels.get('independently_labelled_by_owner') is not True):
        raise ValueError('Use the owner-confirmed labels for this exact fixed sample.')
    answers = labels.get('answers', {})
    if set(answers) != ids or set(predictions) != ids:
        raise ValueError('All 50 distinct owner answers and predictions are required.')
    for values in (answers, predictions):
        if any(v.get('relevance') not in RELEVANCE or v.get('sentiment') not in TONES for v in values.values()):
            raise ValueError('Every source needs an explicit relevance and tone label.')
    exact = sum(answers[k] == {field: predictions[k][field] for field in ('relevance', 'sentiment')} for k in ids)
    tone = sum(answers[k]['sentiment'] == predictions[k]['sentiment'] for k in ids)
    relevance = sum(answers[k]['relevance'] == predictions[k]['relevance'] for k in ids)
    return dict(fingerprint=manifest['fingerprint'], sources=50, exact_matches=exact,
                exact_percent=exact*2, tone_matches=tone, relevance_matches=relevance,
                owner_50_gate_passed=exact >= 40,
                limitations='Requires separate 4/6 hard-case check; this is not investment-return accuracy.')


def render(manifest):
    validate_manifest(manifest)
    payload = canonical(manifest).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    return PAGE.replace('MANIFEST_JSON', payload)


def export(symbols, output):
    from thesis.db import transaction, one
    from thesis.research import sentiment
    packets = []
    with transaction(consistent=True) as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        now = datetime.now(timezone.utc)
        for symbol in sorted(set(symbols)):
            company = one(conn, 'SELECT id FROM instruments WHERE symbol=%s', (symbol,))
            if not company:
                raise ValueError('Choose existing saved companies.')
            packets.append(sentiment.prepare(conn, str(company['id']), now))
    manifest = build(packets)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (output/'evaluation-packets.json').write_text(json.dumps(packets, indent=2, default=str)+'\n')
    (output/'review.html').write_text(render(manifest))
    return dict(sources=50, fingerprint=manifest['fingerprint'], paid_calls=0,
                research_writes=0, ai_suggestions=False)


PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'">
<title>Fledge · Review 50 saved sources</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#0e131b;color:#edf2f8;font-size:16px}
body{margin:0}main{max-width:760px;margin:auto;padding:24px 20px}h1{font-size:24px}h2{font-size:20px;line-height:1.4}
p{line-height:1.6}.muted,small{color:#b0bccb}.evidence{background:#1d2632;border:1px solid #2b3748;border-radius:12px;padding:20px;margin:20px 0}
blockquote{white-space:pre-wrap;overflow-wrap:anywhere;margin:16px 0;border-left:2px solid #536175;padding-left:14px;line-height:1.6}
label{display:block;line-height:1.5;margin:16px 0}select,button{font:inherit;border:1px solid #3a485a;border-radius:6px;background:#1d2632;color:inherit;padding:10px;min-height:44px}
select{display:block;width:100%;margin-top:6px}button{cursor:pointer}button:focus-visible,select:focus-visible{outline:2px solid #9de9d3;outline-offset:3px}
button:disabled{opacity:.5;cursor:default}nav,.row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}.row{justify-content:space-between}
details{margin:20px 0}summary{cursor:pointer;min-height:24px;padding:10px 0}#notice{min-height:24px}.confirm{display:flex;gap:10px;align-items:flex-start}
</style><main><h1>Review 50 saved sources</h1>
<p class="muted">Help check whether Fledge reads company news and discussion correctly. These are saved excerpts, not complete articles. No AI answers or suggestions are shown.</p>
<details><summary>How to label</summary><p>Judge only what this source says about the named company. Relevant means it discusses that company; unrelated means it does not. Use unclear when the connection cannot be established.</p><p>For tone, positive or negative means the wording expresses an evaluation or states a favourable or adverse outcome. Mixed needs both. Neutral is descriptive; unclear means there is not enough evidence. A price target or the amount spent alone does not establish positive or negative tone. Read parent context to understand a reply, while judging the reply's own words.</p></details>
<p id="progress" role="status"></p><p id="position"></p>
<section class="evidence" aria-label="Source evidence"><p class="muted" id="company"></p><h2 id="title"></h2><p class="muted" id="metadata"></p><div id="passages"></div><details id="contextBox"><summary>Saved discussion context</summary><div id="context"></div></details><p class="muted" id="limits"></p></section>
<label>Is this about the named company?<select id="relevance"><option value="">Choose relevance</option><option value="relevant">Relevant</option><option value="unrelated">Unrelated</option><option value="unclear">Unclear</option></select></label>
<label>What tone does it express about that company?<select id="sentiment"><option value="">Choose tone</option><option value="positive">Positive</option><option value="negative">Negative</option><option value="mixed">Mixed</option><option value="neutral">Neutral</option><option value="unclear">Unclear</option></select></label>
<nav aria-label="Review sources"><button id="previous">Previous</button><button id="next">Next</button></nav>
<p id="notice" role="status"></p><p class="muted">Answers save in this browser on this computer. Download them when finished; nothing is sent to Fledge or an AI service. You can change any answer before downloading.</p>
<label class="confirm"><input id="confirm" type="checkbox">I labelled these sources myself without AI suggestions.</label><button id="download" disabled>Download my 50 answers</button>
<script id="manifest" type="application/json">MANIFEST_JSON</script><script>
const manifest=JSON.parse(document.getElementById('manifest').textContent),key='fledge-quality-'+manifest.fingerprint;
let answers={},position=0;const $=id=>document.getElementById(id);
try{answers=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){$('notice').textContent='Browser saving is unavailable. Keep this page open until you download your answers.'}
function text(id,value){$(id).textContent=value}
function quotes(parent,passages){for(const p of passages){const q=document.createElement('blockquote');q.textContent=p.quote;parent.append(q)}}
function complete(){return manifest.cases.filter(c=>answers[c.id]?.relevance&&answers[c.id]?.sentiment).length}
function progress(){text('progress',complete()+' of 50 sources labelled');$('download').disabled=complete()!==50||!$('confirm').checked}
function show(){const c=manifest.cases[position];text('position','Source '+(position+1)+' of 50');text('company',c.company+' · '+c.company_name);text('title',c.title);text('metadata',(c.platform||c.channel)+' · '+new Date(c.published_at).toLocaleString('en-SG',{timeZone:'Asia/Singapore',hour12:false})+' SGT');$('passages').replaceChildren();quotes($('passages'),c.passages.filter(p=>p.id!=='p0'));$('context').replaceChildren();for(const x of c.context){const h=document.createElement('p');h.textContent=x.label;$('context').append(h);quotes($('context'),x.passages)}$('contextBox').hidden=!c.context.length;$('contextBox').open=false;text('limits',c.omitted_fragments?'Some incomplete fragments were excluded from the saved model-visible text.':'Only the saved supplied text is shown.');for(const field of ['relevance','sentiment'])$(field).value=answers[c.id]?.[field]||'';$('previous').disabled=position===0;$('next').disabled=position===49;progress()}
for(const field of ['relevance','sentiment'])$(field).onchange=()=>{const id=manifest.cases[position].id;answers[id]={relevance:$('relevance').value,sentiment:$('sentiment').value};try{localStorage.setItem(key,JSON.stringify(answers));text('notice','Answer saved in this browser.')}catch(e){text('notice','Browser saving is unavailable. Keep this page open.')}progress()};
$('previous').onclick=()=>{position--;show()};$('next').onclick=()=>{position++;show()};$('confirm').onchange=progress;
$('download').onclick=()=>{const payload={fingerprint:manifest.fingerprint,independently_labelled_by_owner:true,answers};const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='fledge-owner-labels-'+manifest.fingerprint.slice(0,8)+'.json';a.click();URL.revokeObjectURL(url)};
show();
</script></main></html>'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    out = sub.add_parser('export')
    out.add_argument('output', type=Path)
    out.add_argument('--symbols', nargs='+', required=True)
    grade = sub.add_parser('score')
    grade.add_argument('manifest', type=Path)
    grade.add_argument('labels', type=Path)
    grade.add_argument('predictions', type=Path)
    args = parser.parse_args()
    if args.command == 'export':
        result = export(args.symbols, args.output)
    else:
        result = score(*(json.loads(getattr(args, field).read_text()) for field in ('manifest','labels','predictions')))
    print(json.dumps(result, indent=2))
