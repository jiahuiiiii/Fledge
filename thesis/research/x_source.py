"""Official X recent-search adapter. No mirrors, cookies or denied-request fallback."""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid5,NAMESPACE_URL
from thesis.db import transaction,one
from thesis.providers.settings import settings
from thesis.service import Conflict
from . import source_hub
from .catalogue import company_alias,mentions
from .market import provider_text
from .sec.service import collection_lock
from .social_threads import save


def parse(raw,company,now):
    if not isinstance(raw,dict) or raw.get('errors'):
        raise ValueError('X returned an incomplete or unavailable search result.')
    if 'data' not in raw and raw.get('meta',{}).get('result_count')!=0:
        raise ValueError('X returned no verified result count or posts.')
    data=raw.get('data',[])
    if not isinstance(data,list):raise ValueError('X returned no readable posts.')
    result=[]
    for item in data[:20]:
        try:
            key=item['id'];body=provider_text(item['text'],6000)
            if not isinstance(key,str) or not re.fullmatch('[1-9][0-9]{0,24}',key):continue
            # Parent context is not part of this adapter. Do not attribute a
            # retweet/quote or an ambiguous reply's target to its author.
            if item.get('referenced_tweets'):continue
            published=datetime.fromisoformat(item['created_at'].replace('Z','+00:00'))
            if published.tzinfo is None or not now-timedelta(days=7)<=published<=now:continue
            if not mentions(body,company['symbol'],company['name']):continue
            author=item.get('author_id')
            result.append(dict(post_key='x:'+key,title='X post',body=body,published_at=published,
                url='https://x.com/i/status/'+key,content_hash=hashlib.sha256(('X post\n'+body).encode()).hexdigest(),
                author_hash=hashlib.sha256(('x:'+author).encode()).hexdigest() if isinstance(author,str) else None))
        except (KeyError,TypeError,ValueError):continue
    return result,len(data)


def refresh(iid,*,fetcher=None,transport=None,lookback_days=7):
    if lookback_days not in (1,7,30):raise ValueError('Unsupported discussion window.')
    if not fetcher and (message:=source_hub.configuration('x')):
        return dict(status='blocked',message=message)
    with transaction() as c:
        if not one(c,"SELECT enabled FROM social_feeds WHERE feed='x'")['enabled']:
            return dict(status='blocked',message='X source access is disabled.')
    company,token=source_hub.begin(iid,'x');now=datetime.now(timezone.utc)
    try:
        alias=company_alias(company['name'])
        alias=re.sub(r'[^\w\s&-]', ' ', alias).strip() if alias else None
        query=f'(${company["symbol"]}' + (f' OR "{alias}"' if alias else '') + ') lang:en -is:retweet -is:reply'
        raw=fetcher(query) if fetcher else json.loads(source_hub.get('x','https://api.x.com/2/tweets/search/recent',
            headers={'Authorization':'Bearer '+settings()['X_BEARER_TOKEN']},
            params={'query':query,'max_results':20,'start_time':(now-timedelta(days=min(7,lookback_days))+timedelta(minutes=1)).isoformat(),
                    'tweet.fields':'created_at,author_id,referenced_tweets'},transport=transport))
        posts,total=parse(raw,company,now)
        posts=[p for p in posts if p["published_at"]>=now-timedelta(days=min(7,lookback_days))]
    except (ValueError,Conflict) as exc:
        return source_hub.finish(iid,'x',token,'failed',str(exc))
    done=datetime.now(timezone.utc)
    with transaction(source=True) as c:
        collection_lock(c)
        done=datetime.now(timezone.utc)
        state=one(c,"SELECT * FROM provider_checks WHERE instrument_id=%s AND provider='x' FOR UPDATE",(iid,))
        if state['attempt_id']!=token or not state['lease_until'] or state['lease_until']<done:raise Conflict('A newer X check replaced this attempt.')
        for post in posts:
            pid=uuid5(NAMESPACE_URL,str(iid)+':x:'+post['post_key']+':'+post['content_hash'])
            c.execute("INSERT INTO social_posts VALUES(%s,%s,'x','x',%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (pid,iid,post['post_key'],post['author_hash'],post['content_hash'],post['title'],post['body'],post['url'],post['published_at'],done))
            save(c,pid,post['post_key'],'post','direct',done)
        message=f'{len(posts)} matching original posts from {total} results. X recent search covers at most seven days; no replies, quotes or reposts are included.'
        c.execute("UPDATE provider_checks SET completed_at=%s,lease_until=NULL,outcome='ready',message=%s,fetched=%s,matched=%s WHERE instrument_id=%s AND provider='x'",(done,message,total,len(posts),iid))
    return dict(status='ready',message=message,matched=len(posts))
