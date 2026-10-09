"""Authored filing controls and controlled HTTP, never actual provider calls."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import httpx
import pytest
from thesis.db import transaction,one
from thesis.research.sec import disclosures,client
from thesis.research.sec.disclosure_text import parse,archive_url,exhibits
from thesis.research.sec.service import add_company
from test_sec_fundamentals import bundle

NOW=datetime.now(timezone.utc)
HTML=('<html><body><h1>Example operating company</h1><div>Item 1. Business</div><p>'+('We sell subscription software to business customers. '*20)+
      '</p><div>Item 1A. Risk factors</div><p>'+('Customer concentration could reduce revenue. '*20)+
      '</p><table><tr><td>Software</td><td>120</td></tr></table></body></html>').encode()


@pytest.fixture(autouse=True)
def disclosure_scope(owner):
    # The common fixture deliberately truncates source rows. Restore this
    # migration's new scope only inside the disposable test database.
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO sources VALUES('sec-disclosures','SEC original filings and earnings releases','sec-public') ON CONFLICT DO NOTHING")


def metadata():
    return deepcopy(bundle(annual=True)['submissions'])


def company():
    return add_company('MSFT')['instrument_id']


def reset_attempt(iid):
    with transaction(admin=True) as conn:
        conn.execute('UPDATE disclosure_refresh_state SET last_attempt_at=NULL WHERE instrument_id=%s',(iid,))


def test_original_text_preserves_words_tables_and_exact_offsets():
    data=parse(HTML,form='10-K',cik=789019)
    assert 'Software | 120' in data['body']
    assert {s['title'] for s in data['sections']}=={'Business','Risk factors'}
    for p in data['passages']:assert data['body'][p['start']:p['end']]==p['quote']


def test_scripts_hidden_xbrl_and_instructions_are_never_executed_or_added():
    data=parse(HTML.replace(b'<h1>',b'<script>steal()</script><ix:hidden>SECRET</ix:hidden><div style="display:none">HIDDEN</div><h1>'),form='10-K',cik=789019)
    assert all(s not in data['body'] for s in ['steal','SECRET','HIDDEN'])


def test_wrong_inline_issuer_is_rejected():
    wrong=b'<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier>'
    with pytest.raises(ValueError,match='another issuer'):parse(HTML.replace(b'<body>',b'<body>'+wrong),form='10-K',cik=789019)


@pytest.mark.parametrize('raw',[b'not a filing',b'<html>short</html>',b'<html>'+b'Request rate threshold exceeded '*20+b'</html>'])
def test_empty_and_access_pages_are_failures(raw):
    with pytest.raises(ValueError):parse(raw,form='10-K',cik=789019)


@pytest.mark.parametrize('filename',['../private.htm','https://evil.test/x.htm','x.htm?secret=1','x.pdf','.hidden.htm'])
def test_archive_paths_are_bounded(filename):
    with pytest.raises(ValueError):archive_url(789019,'0000789019-25-000001',filename)


def test_exhibits_require_explicit_99_and_same_accession():
    url=archive_url(789019,'0000789019-25-000001','main.htm')
    data=dict(links=[('ex99.htm','Exhibit 99.1'),('https://evil.test/ex99.htm','Exhibit 99'),('../other/ex99.htm','Exhibit 99'),('other.htm','Another release'),('ex99.htm','Duplicate')])
    assert exhibits(data,url)==[url.rsplit('/',1)[0]+'/ex99.htm']


def test_plan_rejects_other_issuer_and_incomplete_metadata():
    with pytest.raises(ValueError):disclosures.plan(metadata(),320193,NOW)
    data=metadata();data['filings']['recent']['form']=[]
    with pytest.raises(ValueError):disclosures.plan(data,789019,NOW)


def test_results_filing_is_selected_without_collecting_unrelated_8k():
    data=metadata();recent=data['filings']['recent']
    for key,value in dict(accessionNumber='0000789019-26-000002',form='8-K',filingDate=NOW.date().isoformat(),primaryDocument='results.htm',acceptanceDateTime=(NOW-timedelta(hours=1)).isoformat(),reportDate=NOW.date().isoformat()).items():recent[key].append(value)
    recent['items']=['','2.02,9.01']
    assert len(disclosures.plan(data,789019,NOW))==2
    recent['items'][1]='5.02'
    assert len(disclosures.plan(data,789019,NOW))==1


def test_collect_repeat_and_correction_return_preserve_original_version(owner):
    iid=company();data=metadata()
    def fetch(_):return HTML
    result=disclosures.refresh(iid,fetcher=fetch,submissions=data)
    assert result['status']=='partial' # Explicitly missing quarter/results.
    with transaction() as conn:
        original=disclosures.present(conn,iid)['documents'][0]
    reset_attempt(iid)
    disclosures.refresh(iid,fetcher=lambda _:HTML.replace(b'120',b'121'),submissions=data)
    reset_attempt(iid);disclosures.refresh(iid,fetcher=fetch,submissions=data)
    with transaction() as conn:
        current=disclosures.present(conn,iid)['documents'][0]
        assert current['id']==original['id'] and current['available_at']==original['available_at']
        assert one(conn,'SELECT count(*) n FROM disclosure_documents WHERE instrument_id=%s',(iid,))['n']==2
    with pytest.raises(Exception):
        with transaction(source=True) as conn:conn.execute('UPDATE disclosure_documents SET headline=%s WHERE id=%s',('changed',original['id']))


def test_failure_stops_remaining_requests_and_preserves_prior_documents(owner):
    iid=company();data=metadata();seen=[]
    disclosures.refresh(iid,fetcher=lambda _:HTML,submissions=data);reset_attempt(iid)
    def fail(url):seen.append(url);raise client.SourceFailure('Denied',True)
    result=disclosures.refresh(iid,fetcher=fail,submissions=data)
    assert result['status']=='partial' and len(seen)==1
    with transaction() as conn:
        assert disclosures.present(conn,iid)['documents']
        assert disclosures.present(conn,iid)['source_status']['last_error']


def test_source_permission_withholds_current_and_historical_text(owner):
    iid=company();disclosures.refresh(iid,fetcher=lambda _:HTML,submissions=metadata())
    with transaction() as conn:did=disclosures.present(conn,iid)['documents'][0]['id']
    with transaction(admin=True) as conn:conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-disclosures'")
    try:
        with transaction() as conn:assert disclosures.present(conn,iid)['documents']==[]
        with pytest.raises(ValueError,match='access'):disclosures.document(iid,did)
    finally:
        with transaction(admin=True) as conn:conn.execute("UPDATE sources SET entitlement='sec-public' WHERE id='sec-disclosures'")


def test_expired_collector_cannot_commit(owner):
    iid=company()
    def expire(url):
        with transaction(admin=True) as conn:conn.execute("UPDATE disclosure_refresh_state SET lease_until=now()-interval '1 second' WHERE instrument_id=%s",(iid,))
        return HTML
    result=disclosures.refresh(iid,fetcher=expire,submissions=metadata())
    assert result['status']=='partial'
    with transaction() as conn:assert disclosures.present(conn,iid)['documents']==[]


def test_archive_denial_persists_and_does_not_affect_structured_capability(owner,monkeypatch):
    monkeypatch.setattr(client,'identity',lambda:'Thesis Test contact@test.invalid')
    monkeypatch.setattr(client,'reserve_request',lambda:None)
    with transaction(admin=True) as conn:conn.execute("DELETE FROM provider_clocks WHERE provider='sec-disclosures'")
    calls=[]
    def denied(request):calls.append(request.url);return httpx.Response(403)
    transport=httpx.MockTransport(denied)
    url=archive_url(789019,'0000789019-25-000001','main.htm')
    try:
        with pytest.raises(client.SourceFailure):client.fetch_document(url,transport=transport)
        with pytest.raises(client.SourceFailure):client.fetch_document(url,transport=transport)
        assert len(calls)==1
        with transaction() as conn:assert one(conn,"SELECT denied FROM provider_clocks WHERE provider='sec-disclosures'")['denied']
    finally:
        with transaction(admin=True) as conn:conn.execute("DELETE FROM provider_clocks WHERE provider='sec-disclosures'")


def test_source_role_cannot_read_private_ideas(owner):
    with pytest.raises(Exception):
        with transaction(source=True) as conn:conn.execute('SELECT * FROM theses')


def test_later_amendment_of_old_period_does_not_replace_new_annual():
    data=metadata();recent=data['filings']['recent']
    values=dict(accessionNumber='0000789019-26-000002',form='10-K/A',filingDate=NOW.date().isoformat(),primaryDocument='amended.htm',acceptanceDateTime=(NOW-timedelta(minutes=10)).isoformat(),reportDate='2024-06-30')
    for key,value in values.items():recent[key].append(value)
    chosen=disclosures.plan(data,789019,NOW)
    assert chosen[0]['accession']==metadata()['filings']['recent']['accessionNumber'][0]
    assert chosen[0]['period_end']>'2024-06-30'


def test_archive_denial_arriving_during_wait_stops_dispatch(owner,monkeypatch):
    monkeypatch.setattr(client,'identity',lambda:'Thesis Test contact@test.invalid')
    with transaction(admin=True) as conn:conn.execute("DELETE FROM provider_clocks WHERE provider='sec-disclosures'")
    def reserve():
        with transaction(source=True) as conn:conn.execute("UPDATE provider_clocks SET denied=true WHERE provider='sec-disclosures'")
    monkeypatch.setattr(client,'reserve_request',reserve)
    try:
        with pytest.raises(client.SourceFailure,match='changed while waiting'):
            client.fetch_document(archive_url(789019,'0000789019-25-000001','main.htm'),transport=httpx.MockTransport(lambda _:pytest.fail('A newly denied request was sent')))
        with transaction() as conn:assert one(conn,"SELECT requests FROM provider_clocks WHERE provider='sec-disclosures'")['requests']==0
    finally:
        with transaction(admin=True) as conn:conn.execute("DELETE FROM provider_clocks WHERE provider='sec-disclosures'")
