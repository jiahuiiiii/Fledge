"""Alert eligibility is separate from tone; these are structural, offline controls."""
from copy import deepcopy
import pytest
from thesis.research import reporting_basis as R, coverage, sentiment
from thesis.monitoring.news_watch import changes
from test_news_coverage import source, analyse, relation


def test_reporting_requires_own_complete_source_and_relevance():
 s=source('item_1','Microsoft confirmed a breach.')
 out=R.render(R.Evidence(impact='not_stated',kind='reported_event',passages=['p1']),s,'relevant')
 assert out['eligible'] and out['citations'][0]['quote']==s['text']
 for value in [None,R.Evidence(impact='not_stated',kind='reported_event',passages=[]),R.Evidence(impact='not_stated',kind='opinion_only',passages=['p1']),R.Evidence(impact='not_stated',kind='reported_event',passages=['p999']),R.Evidence(impact='not_stated',kind='reported_event',passages=['p1','p1'])]:
  with pytest.raises(ValueError):R.render(value,s,'relevant')
 with pytest.raises(ValueError):R.render(R.Evidence(impact='not_stated',kind='reported_event',passages=['p1']),s,'unrelated')


@pytest.mark.parametrize('kind',['opinion_only','conditional_only','question_only','insufficient_detail','not_applicable'])
def test_negative_sentiment_can_remain_visible_without_a_reporting_alert(kind):
 old=analyse([source('old','Microsoft update.')],[])
 s=source('new','Microsoft could suffer a decline.',1)
 new=analyse([s],[])
 new['result']['items'][0]['reporting_basis']=R.render(R.Evidence(impact='not_stated',kind=kind,passages=[]),s,'relevant')
 assert new['result']['items'][0]['sentiment']=='negative'
 assert changes(old,new)==[]


@pytest.mark.parametrize('kind',['reported_event','unconfirmed_event'])
def test_concrete_adverse_reports_remain_alertable_and_seen_inputs_are_quiet(kind):
 old=analyse([source('old','Microsoft update.')],[])
 s=source('new','Microsoft reported a material decline.',1);new=analyse([s],[])
 new['result']['items'][0]['reporting_basis']=R.render(R.Evidence(impact='adverse',kind=kind,passages=['p1']),s,'relevant')
 assert changes(old,new)[0]['kind']=='new_reporting'
 assert changes(new,new)==[]
 assert changes(old,new,{('news','content:new')})==[]


def test_identical_cited_body_under_new_headline_is_not_changed_evidence():
 old=source('item_1','Microsoft announced a centre.',0)
 new=source('item_2',old['text'],1)
 new['passages'][0]['quote']='Another headline for Microsoft'
 a=analyse([old,new],[relation(kind='adds_detail')],tones={'item_1':'neutral','item_2':'neutral'})
 link=a['result']['coverage_links'][0]
 assert link['change_evidence']=='unchanged_excerpts'
 assert not coverage.change_for_review(link)
 previous=analyse([old],[],tones={'item_1':'neutral'})
 assert changes(previous,a)==[]


def test_new_headline_correction_still_alerts_when_that_change_is_cited():
 old=source('item_1','Microsoft announced a centre.',0)
 new=source('item_2',old['text'],1)
 new['passages'][0]['quote']='Microsoft denies the centre announcement'
 link=relation(kind='contradicts');link['item_passages']=['p0']
 a=analyse([old,new],[link],tones={'item_1':'neutral','item_2':'neutral'})
 assert coverage.change_for_review(a['result']['coverage_links'][0])
 assert changes(analyse([old],[],tones={'item_1':'neutral'}),a)[0]['kind']=='new_reporting'


def test_schema_keeps_reporting_news_only_and_policy_in_cache_identity():
 news=source('item_1','Microsoft announced a centre.')
 social=source('item_2','I like Microsoft.',channel='social')
 p=dict(company={'symbol':'MSFT','name':'Microsoft'},sources=[news,social],comparison_sources=[],reporting_policy=R.POLICY)
 schema=sentiment.request_for(p)['text']['format']['schema']
 branches=schema['properties']['items']['items']['anyOf']
 assert 'reporting' in branches[0]['required']
 assert 'reporting' not in branches[1]['properties']
 historical=deepcopy(p);historical.pop('reporting_policy')
 assert sentiment.model_identity(p)!=sentiment.model_identity(historical)


def test_article_tone_cannot_turn_neutral_event_into_adverse_alert():
 old=analyse([source('old','Microsoft update.')],[])
 s=source('new','Microsoft announced a product. Some analysts worry about a hypothetical future.',1)
 new=analyse([s],[])
 new['result']['items'][0]['reporting_basis']=R.render(R.Evidence(kind='reported_event',impact='not_stated',passages=['p1']),s,'relevant')
 assert new['result']['items'][0]['sentiment']=='negative'
 assert changes(old,new)==[]


def test_reworded_teaser_cannot_realert_an_identical_reported_adverse_event():
 old=source('item_1','Microsoft confirmed a breach exposed customer data.',0)
 new=source('item_2',old['text'],1)
 new['passages'][0]['quote']='More on the Microsoft breach'
 link=relation(kind='adds_detail');link['item_passages']=['p0','p1']
 after=analyse([new],[link],comparisons=[old])
 after['result']['items'][0]['reporting_basis']=R.render(R.Evidence(kind='reported_event',impact='adverse',passages=['p1']),new,'relevant')
 assert changes(analyse([old],[]),after)==[]
 # A real changed claim in the new headline remains reviewable when cited.
 new['passages'][0]['quote']='Microsoft confirms that the breach exposed another 500 accounts'
 after=analyse([new],[link],comparisons=[old])
 after['result']['items'][0]['reporting_basis']=R.render(R.Evidence(kind='reported_event',impact='adverse',passages=['p0','p1']),new,'relevant')
 assert changes(analyse([old],[]),after)[0]['kind']=='new_reporting'
