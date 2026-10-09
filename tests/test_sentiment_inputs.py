"""Current raw selection is read-only and never borrows saved AI labels."""

from datetime import datetime, timezone, timedelta
import json
import pytest
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import sentiment as S, sentiment_inputs as I, conversation as C
from thesis.research.sec.service import add_company
from thesis import service
from test_market import prepare, commit, news
from test_sentiment import provider, add_social, feed
from test_conversation import setup, fetcher, unlock


def preview(iid, now=None):
    with transaction(consistent=True) as c:
        return I.current(c, iid, now)


def test_first_read_needs_no_analysis_and_is_readonly(owner, monkeypatch):
    iid = prepare(owner)
    add_social(iid)
    budget = ledger.snapshot()
    monkeypatch.setattr(
        ledger, "execute", lambda *_a, **_k: pytest.fail("Reading called model")
    )
    data = preview(iid)
    assert data["status"] == "no_saved_reading"
    assert len(data["sources"]) == 2 and data["scopes"]["reddit"]["selected"] == 1
    assert data["scopes"]["news"]["added"] is None
    assert all(s["in_saved_sample"] is None for s in data["sources"])
    assert ledger.snapshot() == budget
    assert not any(
        key in s
        for s in data["sources"]
        for key in (
            "sentiment",
            "relevance",
            "author_hash",
            "conversation",
            "explanation",
        )
    )
    assert service.state(owner, iid)["sentiment_inputs"]["status"] == "no_saved_reading"


def test_matching_selection_does_not_mean_new_or_current_model_output(owner):
    iid = prepare(owner)
    reading = S.generate(iid, transport=provider())
    data = preview(iid)
    assert data["status"] == "same" and data["scopes"]["news"] == dict(
        selected=1, available=1, added=0, no_longer_selected=0, retained=1
    )
    assert data["saved_cutoff"] == reading["cutoff"]
    assert data["sources"][0]["in_saved_sample"]
    assert "summary" not in data


def test_new_source_is_not_labeled_by_earlier_reading(owner):
    iid = prepare(owner)
    old = S.generate(iid, transport=provider("negative"))
    commit(
        iid,
        [
            news(
                id=2,
                url="https://example.test/later",
                headline="Microsoft announces a product plan",
                summary="This is a newly saved authored report.",
            )
        ],
    )
    data = preview(iid)
    assert data["status"] == "changed" and data["scopes"]["news"]["added"] == 1
    assert len([s for s in data["sources"] if s["in_saved_sample"] is False]) == 1
    with transaction() as c:
        assert S.latest(c, iid) == old


def test_corrected_version_is_distinct_without_claiming_a_new_event(owner):
    iid = prepare(owner)
    old = S.generate(iid, transport=provider())
    old_id = old["sources"][0]["id"]
    commit(
        iid, [news(summary="Microsoft now confirms the previously reported contract.")]
    )
    data = preview(iid)
    assert data["status"] == "changed"
    assert old_id not in {s["id"] for s in data["sources"]}
    assert (
        data["scopes"]["news"]["added"]
        == data["scopes"]["news"]["no_longer_selected"]
        == 1
    )
    with transaction() as c:
        row = one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (old["id"],))
        assert S.present(c, row) == old


def test_parent_changes_are_separate_from_selected_text_changes(owner):
    iid, post, child, parent = setup(owner)
    S.generate(iid, transport=provider())
    C.collect(post["id"], fetcher=fetcher(child, parent, []))
    data = preview(iid)
    assert data["status"] == "changed" and data["parents_changed"] == 1
    assert all(s["added"] == 0 for s in data["scopes"].values())
    S.generate(iid, transport=provider())
    unlock(post["id"])
    C.collect(post["id"], fetcher=fetcher(child, parent, []))
    assert preview(iid)["status"] == "same"
    aged = preview(iid, datetime.now(timezone.utc) + timedelta(hours=25))
    assert aged["status"] == "changed" and aged["parents_changed"] == 1
    assert aged["parent_contexts"] == 0


def test_withheld_baseline_does_not_leak_old_sources_or_comparison_counts(owner):
    iid = prepare(owner)
    add_social(iid, feed(body="Microsoft opinion with distinctive withheld wording."))
    S.generate(iid, transport=provider())
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false WHERE feed<>'hackernews'")
    try:
        data = preview(iid)
        assert data["status"] == "saved_reading_withheld"
        assert "distinctive withheld wording" not in json.dumps(data)
        assert all(
            s["added"] is None and s["retained"] is None
            for s in data["scopes"].values()
        )
        assert (
            data["parents_changed"] is None
            and data["comparison_sources_changed"] is None
        )
        assert data["sources"] and all(
            s["in_saved_sample"] is None for s in data["sources"]
        )
    finally:
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=true")


def test_removed_child_is_not_visible_in_current_preview(owner):
    iid, post, child, parent = setup(owner)
    S.generate(iid, transport=provider())
    child["deleted"] = True
    C.collect(post["id"], fetcher=fetcher(child, parent, []))
    data = preview(iid)
    assert data["status"] == "saved_reading_withheld"
    assert str(post["id"]) not in {s["id"] for s in data["sources"]}


def test_empty_and_expired_selection_are_not_neutral_or_old_raw_data(owner):
    iid = add_company("MSFT")["instrument_id"]
    assert preview(iid)["status"] == "empty"
    commit(iid, [news()])
    S.generate(iid, transport=provider())
    data = preview(iid, datetime.now(timezone.utc) + timedelta(days=8))
    assert data["status"] == "empty" and not data["sources"]
    assert data["scopes"]["news"]["no_longer_selected"] == 1


def test_candidate_count_survives_ineligible_fragments(owner):
    iid = add_company("MSFT")["instrument_id"]
    commit(iid, [news(headline="Microsoft ...", summary="Unfinished ...")])
    data = preview(iid)
    assert data["status"] == "empty" and data["scopes"]["news"]["available"] == 1
    with transaction() as c:
        with pytest.raises(ValueError, match="No complete recent"):
            S.prepare(c, iid)


def test_all_candidates_are_eligible_and_older_new_report_enters_analysis(owner):
    iid = add_company("MSFT")["instrument_id"]
    now = datetime.now(timezone.utc)
    reports = [
        news(
            id=i + 1,
            url=f"https://example.test/{i}",
            headline=f"Microsoft report {i}",
            summary=f"Authored report number {i} is complete.",
            datetime=int((now - timedelta(minutes=i + 1)).timestamp()),
        )
        for i in range(20)
    ]
    commit(iid, reports)
    S.generate(iid, transport=provider())
    data = preview(iid)
    assert len(data["sources"]) == 20 and data["comparison_news"] == 0
    assert data["scopes"]["news"]["available"] == 20
    commit(
        iid,
        [
            news(
                id=99,
                url="https://example.test/older",
                headline="Microsoft older report",
                summary="This report is only in the comparison pool.",
                datetime=int((now - timedelta(minutes=55)).timestamp()),
            )
        ],
    )
    changed = preview(iid)
    assert changed["status"] == "changed" and not changed["comparison_sources_changed"]
    assert changed["scopes"]["news"]["added"] == 1
    assert "only in the comparison pool" in str(changed["sources"])


def test_future_available_source_cannot_enter_earlier_selection(owner):
    iid = prepare(owner)
    cutoff = datetime.now(timezone.utc)
    commit(
        iid,
        [
            news(
                id=2,
                url="https://example.test/after",
                summary="A distinct report acquired later.",
            )
        ],
    )
    data = preview(iid, cutoff)
    assert "acquired later" not in str(data["sources"])


def test_recorded_fixture_is_not_a_live_input_preview(owner):
    from thesis.fixtures import INSTRUMENT

    assert preview(INSTRUMENT) is None
