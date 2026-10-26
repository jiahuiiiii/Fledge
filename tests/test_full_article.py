"""Full-article briefs for alerts: invented pages and model answers, no network."""
import json
import urllib.request
from uuid import uuid4
import pytest
from thesis.monitoring import telegram as T, news_watch
from thesis.monitoring.telegram_message import render
from thesis.providers import ledger, settings
from thesis.research import full_article as F, sentiment
from test_model_budget import clean_model_ledger  # noqa: F401
from test_telegram import bot, link, unpace, all_deliveries  # noqa: F401
from test_idea_alerts import setup
from test_market import commit, news
from test_sentiment import provider as sentiment_provider

HEADLINE = "Broadcom to Advance NTT DOCOMO Private Cloud with VMware Cloud Foundation"
PARAGRAPHS = [
    "Broadcom said on Monday that NTT DOCOMO signed its first ten-year VMware software agreement in Japan.",
    "The agreement covers VMware Cloud Foundation across the operator's private cloud, the companies said.",
] + [f"Paragraph {i} gives further detail about the deployment, its schedule and the services it will support for customers." for i in range(20)]


def page(paragraphs=PARAGRAPHS, title=HEADLINE, extra=""):
    body = "".join(f"<p>{p}</p>" for p in paragraphs)
    return (f"<html><head><title>{title}</title><script>var x='<p>not text</p>'</script></head>"
            f"<body><nav><p>Home Markets Videos Sign in to read later</p></nav>{extra}<article>{body}</article>"
            f"<footer><p>Copyright notice and links to every other section of the site.</p></footer></body></html>")


def test_extract_keeps_article_paragraphs_only():
    passages = F.extract(page(), HEADLINE, 130)
    assert passages[0] == PARAGRAPHS[0]
    assert not any("Home Markets" in p or "Copyright" in p or "not text" in p for p in passages)
    assert sum(map(len, passages)) <= F.MAX_TEXT


@pytest.mark.parametrize("html,reason", [
    (page(["Subscribe to continue reading this article about Broadcom and NTT DOCOMO VMware Cloud Foundation."]), "paywall"),
    (page(title="Weather today", paragraphs=["Rain is expected across the region this afternoon, with cooler air." * 30]), "headline"),
    (page(paragraphs=PARAGRAPHS[:2]), "preview"),
])
def test_extract_rejects_paywall_wrong_page_and_short_text(html, reason):
    with pytest.raises(F.Unavailable, match=reason):
        F.extract(html, HEADLINE, 130)


def test_only_allow_listed_https_sites_are_fetched_or_followed(monkeypatch):
    monkeypatch.setattr(F, "_open", lambda url: pytest.fail("fetched a blocked site"))
    for url in ("https://www.wsj.com/a", "http://finance.yahoo.com/a", "https://user@finance.yahoo.com/a",
                "https://finance.yahoo.com:8443/a", "javascript:alert(1)", None):
        with pytest.raises(F.Unavailable):
            F.fetch(dict(url=url, title=HEADLINE, body="x"))
    handler = F._Redirects()
    req = urllib.request.Request("https://finnhub.io/api/news?id=1")
    with pytest.raises(F.Unavailable, match="not on the list"):
        handler.redirect_request(req, None, 302, "Found", {}, "https://www.wsj.com/articles/x")
    monkeypatch.setattr(F, "_open", lambda url: ("https://www.barchart.com/story", page()))
    with pytest.raises(F.Unavailable, match="allowed site"):
        F.fetch(dict(url="https://finnhub.io/api/news?id=1", title=HEADLINE, body="x"))


def answer(points):
    text = json.dumps(dict(points=points))
    return dict(response_body=dict(output=[dict(type="message", content=[dict(type="output_text", text=text)])]))


def test_points_require_exact_quotes_from_the_named_passage():
    good = dict(sentence="NTT DOCOMO signed a ten-year VMware deal with Broadcom.", passage_id="p0",
                quote="NTT DOCOMO signed its first ten-year VMware software agreement in Japan")
    assert F.points(answer([good]), PARAGRAPHS)[0]["sentence"].startswith("NTT DOCOMO")
    for bad in (dict(good, quote="NTT DOCOMO signed a twenty-year VMware software agreement in Japan"),
                dict(good, passage_id="p1"),
                dict(good, quote="first ten-year VMware"),
                dict(good, passage_id="p99")):
        with pytest.raises(F.Unavailable):
            F.points(answer([bad]), PARAGRAPHS)
    with pytest.raises(F.Unavailable, match="no specific development"):
        F.points(answer([]), PARAGRAPHS)
    with pytest.raises(F.Unavailable, match="not readable"):
        F.points(dict(response_body=dict(output=[])), PARAGRAPHS)


def luna(points):
    def provider(request):
        assert request["model"] == settings.OPENAI_SENTIMENT_MODEL
        assert request["text"]["format"]["name"] == "alert_article_brief"
        return dict(id="resp_" + uuid4().hex, model=settings.OPENAI_SENTIMENT_MODEL, service_tier="default",
                    status="completed", usage=dict(input_tokens=2000, output_tokens=150, total_tokens=2150,
                                                   input_tokens_details=dict(cached_tokens=0)),
                    output=[dict(type="message", content=[dict(type="output_text", text=json.dumps(dict(points=points)))])])
    return provider


SOURCE = dict(id="s1", url="https://finance.yahoo.com/news/broadcom", title=HEADLINE, body="Broadcom preview.")
POINT = dict(sentence="NTT DOCOMO signed a ten-year VMware deal with Broadcom.", passage_id="p0",
             quote="NTT DOCOMO signed its first ten-year VMware software agreement in Japan")


def fetched(source):
    return dict(url=source["url"], final_url=source["url"], passages=PARAGRAPHS, fetched_at="2026-10-20T07:00:00Z")


def test_brief_is_recorded_at_luna_rates_reused_and_never_resent(monkeypatch):
    monkeypatch.setattr(settings, "SENTIMENT_MODEL", settings.OPENAI_SENTIMENT_MODEL)
    result = F.brief(SOURCE, "Broadcom Inc.", transport=luna([POINT]), fetcher=fetched)
    assert result["kind"] == "full" and result["points"][0]["quote"] == POINT["quote"]
    from thesis.db import transaction, one
    with transaction() as c:
        call = one(c, "SELECT purpose,price_version,status FROM model_calls WHERE id=%s", (result["call_id"],))
    assert call == dict(purpose=F.PURPOSE, price_version=ledger.LUNA_ARTICLE_BRIEF_PRICE_VERSION, status="settled")
    again = F.brief(SOURCE, "Broadcom Inc.", transport=lambda _: pytest.fail("paid twice"), fetcher=fetched)
    assert again["call_id"] == result["call_id"]

    def timeout(_):
        raise TimeoutError("invented")
    other = dict(SOURCE, title=HEADLINE + " update")
    assert F.brief(other, "Broadcom Inc.", transport=timeout, fetcher=fetched)["kind"] == "preview"
    later = F.brief(other, "Broadcom Inc.", transport=lambda _: pytest.fail("resent"), fetcher=fetched)
    assert later == dict(kind="preview", reason="an earlier brief request has no settled response")


def test_any_failure_keeps_the_preview(monkeypatch):
    monkeypatch.setattr(settings, "SENTIMENT_MODEL", settings.OPENAI_SENTIMENT_MODEL)

    def blocked(source):
        raise F.Unavailable("paywall")
    assert F.brief(SOURCE, "Broadcom Inc.", transport=luna([POINT]), fetcher=blocked) == dict(kind="preview", reason="paywall")
    wrong = dict(POINT, quote="NTT DOCOMO signed a deal that the article never mentions at all")
    assert F.brief(SOURCE, "Broadcom Inc.", transport=luna([wrong]), fetcher=fetched)["kind"] == "preview"

    def broken(source):
        raise RuntimeError("anything else")
    assert F.brief(SOURCE, "Broadcom Inc.", fetcher=broken)["kind"] == "preview"


def test_luna_rates_apply_only_to_the_bounded_brief(monkeypatch):
    monkeypatch.setattr(settings, "SENTIMENT_MODEL", settings.OPENAI_SENTIMENT_MODEL)
    body = F.request_for("Broadcom Inc.", HEADLINE, PARAGRAPHS)
    assert ledger.request_profile(body).version == ledger.LUNA_ARTICLE_BRIEF_PRICE_VERSION
    with pytest.raises(ValueError):
        ledger.request_profile(dict(body, max_output_tokens=12000))


def alert_record(briefs):
    item = dict(source_id="s1", channel="news", sentiment="neutral", importance=dict(level="high", category="deal"),
                reporting_basis=dict(kind="reported_event", impact="not_stated",
                                     citations=[dict(quote="Broadcom to advance NTT DOCOMO's private cloud")]))
    detail = dict(symbol="AVGO", payload=dict(kind="important_reporting", items=[item]),
                  sources=[dict(SOURCE)], article_briefs=briefs)
    if briefs is None:
        detail.pop("article_briefs")
    return dict(kind="company", title="New company developments to review", created_at="2026-10-20T03:01:00Z", detail=detail)


def test_message_labels_full_article_or_preview_only():
    full = render(alert_record({"s1": dict(kind="full", points=[POINT], url=SOURCE["url"])}))
    assert "<b>What happened · Full article</b>\nNTT DOCOMO signed a ten-year VMware deal with Broadcom." in full
    assert "“NTT DOCOMO signed its first ten-year VMware software agreement in Japan”" in full
    preview = render(alert_record({"s1": dict(kind="preview", reason="paywall")}))
    assert "<b>Source excerpt · Preview only</b>" in preview and "Full article" not in preview
    off = render(alert_record(None))
    assert "<b>Source excerpt</b>" in off and "Preview only" not in off


def company_alert(owner, bot):
    iid, _, _ = setup(owner, True)
    news_watch.configure(owner, iid, True)
    link(owner, bot)
    T.configure(owner, True)
    commit(iid, [news(id=901, url="https://finance.yahoo.com/news/cost-warning", headline="Microsoft reports a cost warning",
                      summary="Microsoft reports cost pressure, with demand still uncertain.")])
    change = sentiment.generate(iid, transport=sentiment_provider("negative"))
    news_watch.publish(owner, iid, change["id"])


def send_all(owner):
    for _ in range(6):
        unpace(owner)
        T.run_once(owner)


def test_sender_prepares_the_brief_before_sending(owner, bot, monkeypatch):
    company_alert(owner, bot)
    monkeypatch.setattr(F, "enabled", lambda: True)
    seen = []

    def for_alert(record, **kw):
        seen.append(record["detail"]["symbol"])
        sid = str(record["detail"]["payload"]["items"][0]["source_id"])
        return {sid: dict(kind="full", points=[dict(sentence="Microsoft warned that costs are rising.",
                                                     quote="Microsoft reports cost pressure, with demand still uncertain",
                                                     passage_id="p0")], url="https://finance.yahoo.com/x")}
    monkeypatch.setattr(F, "for_alert", for_alert)
    send_all(owner)
    company = [d for d in all_deliveries(owner) if d["kind"] == "company"]
    assert company and all(d["status"] == "sent" for d in company)
    text = next(m["text"] for m in bot.sent if "Full article" in m["text"])
    assert "Microsoft warned that costs are rising." in text and seen


def test_failed_preparation_still_sends_the_preview(owner, bot, monkeypatch):
    company_alert(owner, bot)
    monkeypatch.setattr(F, "enabled", lambda: True)

    def broken(record, **kw):
        raise RuntimeError("invented")
    monkeypatch.setattr(F, "for_alert", broken)
    send_all(owner)
    company = [d for d in all_deliveries(owner) if d["kind"] == "company"]
    assert company and all(d["status"] == "sent" for d in company)
    assert not any("Full article" in m["text"] for m in bot.sent)
