"""Question-to-original-answer pairing is checked before private publication."""

import pytest
from thesis.db import transaction, one
from thesis.research import idea_alerts as A
from thesis import review_digest
from test_idea_alerts import setup, provider


@pytest.mark.parametrize(
    "kind", ["direct_answer", "partial_answer", "explicit_negative_answer"]
)
def test_answer_pairs_exact_saved_target_and_original_source(owner, kind):
    iid, _, reading = setup(owner)

    def change(items):
        for i in items:
            i["answer_kind"] = kind
        return items

    result = A.generate(
        owner, iid, reading["id"], transport=provider("answers", mutate=change)
    )
    with transaction(owner) as c:
        shown = A.list_for(c, owner)[0]
        assert shown["published"] and shown["noteworthy_count"] == 1
        item = shown["items"][0]
        assert item["answer_target"] in item["reasoning_quote"]
        assert item["answer_excerpt"] in next(
            q["quote"]
            for q in item["citations"]
            if q["passage_id"] == item["answer_passage_id"]
        )
        assert item["answer_kind_label"] == A.ANSWER_LABELS[kind]
    for html in [A.download(owner, result["id"])[1], review_digest.download(owner)[1]]:
        assert (
            "Answer evidence · original wording" in html
            and "Question addressed:" in html
        )
        assert item["answer_excerpt"] in html


@pytest.mark.parametrize(
    "kind",
    ["source_question", "missing_information", "background_only", "not_applicable"],
)
def test_non_answer_categories_remain_quiet(owner, kind):
    iid, _, reading = setup(owner)

    def change(items):
        for i in items:
            i["answer_kind"] = kind
        return items

    result = A.generate(
        owner, iid, reading["id"], transport=provider("context", mutate=change)
    )
    with transaction(owner) as c:
        shown = A.list_for(c, owner)[0]
        assert shown["noteworthy_count"] == 0 and not shown["published"]
        assert not one(
            c,
            "SELECT 1 FROM idea_alert_publications WHERE check_id=%s",
            (result["id"],),
        )


@pytest.mark.parametrize(
    "fault",
    [
        "missing_kind",
        "question_as_answer",
        "missing_as_answer",
        "background_as_answer",
        "answer_as_context",
        "no_target",
        "no_excerpt",
        "blank_target",
        "blank_excerpt",
        "foreign_target",
        "foreign_excerpt",
        "unselected_excerpt",
        "parent_only_excerpt",
        "non_answer_target",
        "non_answer_excerpt",
    ],
)
def test_invalid_answer_evidence_never_publishes(owner, fault):
    if fault == "parent_only_excerpt":
        from test_idea_context import case

        iid, _, _, _, _, reading = case(owner)
    else:
        iid, _, reading = setup(owner)
    with transaction(owner) as c:
        packet, _ = A.prepare(c, owner, iid, reading["id"])

    def change(items):
        i = items[0]
        if fault == "missing_kind":
            i.pop("answer_kind")
        elif fault.endswith("_as_answer"):
            i["answer_kind"] = {
                "question_as_answer": "source_question",
                "missing_as_answer": "missing_information",
                "background_as_answer": "background_only",
            }[fault]
        elif fault == "answer_as_context":
            i.update(relation="context", connection_basis="background")
        elif fault == "no_target":
            i["answer_target"] = None
        elif fault == "no_excerpt":
            i["answer_excerpt"] = None
        elif fault == "blank_target":
            i["answer_target"] = "     "
        elif fault == "blank_excerpt":
            i["answer_excerpt"] = "      "
        elif fault == "foreign_target":
            i["answer_target"] = "Did another company renew its clients?"
        elif fault == "foreign_excerpt":
            i["answer_excerpt"] = "An invented numerical result of 72 percent."
        elif fault == "unselected_excerpt":
            # The mock selected the title p0; the full body is not selected evidence.
            i["answer_excerpt"] = next(
                p["quote"]
                for p in packet["sources"][0]["passages"]
                if p["id"] not in i["passages"]
            )
        elif fault == "parent_only_excerpt":
            index, source = next(
                (n, s) for n, s in enumerate(packet["sources"]) if s.get("conversation")
            )
            parent_quote = source["conversation"]["passages"][0]["quote"]
            assert parent_quote not in source["text"]
            items[index]["answer_excerpt"] = parent_quote
        else:
            i.update(
                relation="context",
                connection_basis="background",
                answer_kind="background_only",
            )
            if fault == "non_answer_target":
                i["answer_excerpt"] = None
            else:
                i["answer_target"] = None
        return items

    with pytest.raises(ValueError):
        A.generate(
            owner, iid, reading["id"], transport=provider("answers", mutate=change)
        )
    with transaction(owner) as c:
        assert not one(c, "SELECT 1 FROM idea_alert_checks WHERE owner_id=%s", (owner,))


def test_source_specific_schema_requires_answer_fields_without_weakening_question_route(
    owner,
):
    iid, _, reading = setup(owner)
    with transaction(owner) as c:
        p, _ = A.prepare(c, owner, iid, reading["id"])
    broad = A.request_for(p)["text"]["format"]["schema"]["properties"]["items"][
        "items"
    ]["anyOf"][0]
    assert {"answer_kind", "answer_target", "answer_excerpt"} <= set(broad["required"])
    p["purpose"] = "question"
    question = A.request_for(p)["text"]["format"]["schema"]["properties"]["items"][
        "items"
    ]["anyOf"][0]
    assert not {"answer_kind", "answer_target", "answer_excerpt"} & set(
        question["properties"]
    )
    assert question["properties"]["reasoning_segment_id"] == {"type": "null"}


@pytest.mark.parametrize("basis", ["direct_evidence", "source_argument"])
def test_source_form_can_remain_background_without_claiming_an_answer(owner, basis):
    iid, _, reading = setup(owner)

    def change(items):
        for i in items:
            i["connection_basis"] = basis
        return items

    result = A.generate(
        owner, iid, reading["id"], transport=provider("context", mutate=change)
    )
    with transaction(owner) as c:
        shown = A.list_for(c, owner)[0]
    assert shown["noteworthy_count"] == 0 and not shown["published"]
    assert all(
        i["connection_basis_label"] == A.CONTEXT_BASIS_LABELS[basis]
        and i["answer_excerpt"] is None
        for i in shown["items"]
    )


def test_retained_actual_quiet_opinion_is_valid_background_without_new_paid_call():
    import os, json
    from pathlib import Path

    path = os.environ.get("THESIS_ANSWER_CORPUS")
    if not path:
        pytest.skip("Set the retained substantive-answer evaluation directory")
    p = Path(path) / "bounded-9000"
    frozen = json.loads((p / "frozen.json").read_text())["cases"][
        "MSFT-paid-retention-control"
    ]
    call = json.loads((p / "MSFT-paid-retention-control-call.json").read_text())
    assert A.request_for(frozen["packet"]) == frozen["request"]
    result = A.render(call, frozen["packet"])
    assert result["noteworthy_count"] == 0 and len(result["items"]) == 15
    item = next(
        i for i in result["items"] if i["connection_basis"] == "source_argument"
    )
    assert item["relation"] == "context" and item["answer_excerpt"] is None
    assert item["connection_basis_label"] == A.CONTEXT_BASIS_LABELS["source_argument"]
