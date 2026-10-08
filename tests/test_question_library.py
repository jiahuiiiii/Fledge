from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from pydantic import ValidationError
from thesis.config import INSTRUMENT, OWNER
from thesis.db import transaction, one
from thesis.research import question_library as library
from thesis import service


def test_questions_persist_per_company_without_idea_or_watch(owner):
    with transaction() as conn:
        other = str(one(conn, "SELECT id FROM instruments WHERE symbol='AURQ'")["id"])
    library.save(owner, INSTRUMENT, library.SaveQuestion(question="Can margins recover?"))
    library.save(owner, INSTRUMENT, library.SaveQuestion(question="How concentrated are customers?"))
    library.save(owner, other, library.SaveQuestion(question="Will shipments recover?"))
    state = service.state(owner, INSTRUMENT)
    assert len(state["question_library"]["items"]) == 2
    assert state["question_library"]["selected_question"] == "How concentrated are customers?"
    assert state["thesis"] is None and state["news_watch"] is None
    assert service.state(owner, other)["question_library"]["selected_question"] == "Will shipments recover?"
    with transaction(owner) as conn:
        assert one(conn, "SELECT count(*) n FROM model_calls")["n"] == 0
        assert one(conn, "SELECT count(*) n FROM research_actions")["n"] == 0


def test_duplicate_selection_preserves_original_spelling(owner):
    first = library.save(owner, INSTRUMENT, library.SaveQuestion(question=" Can   margins recover? "))
    again = library.save(owner, INSTRUMENT, library.SaveQuestion(question="can margins recover?"))
    assert len(again["items"]) == 1
    assert first["items"][0]["id"] == again["items"][0]["id"]
    assert again["selected_question"] == "Can margins recover?"


def test_concurrent_adds_keep_questions_and_one_selection(owner):
    values = ["Can margins recover?", "Will sales recover?", "Can margins recover?"]
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda q: library.save(owner, INSTRUMENT, library.SaveQuestion(question=q)), values))
    with transaction(owner) as conn:
        result = library.present(conn, owner, INSTRUMENT)
        assert len(result["items"]) == 2
        assert sum(i["selected"] for i in result["items"]) == 1


def test_private_questions_cannot_cross_owners_or_source_role(owner):
    library.save(owner, INSTRUMENT, library.SaveQuestion(question="Can margins recover?"))
    with transaction(OWNER) as conn:
        assert library.present(conn, owner, INSTRUMENT)["items"] == []
        assert conn.execute("UPDATE research_question_library SET selected=false WHERE owner_id=%s", (owner,)).rowcount == 0
    with transaction() as conn:
        assert one(conn, "SELECT count(*) n FROM research_question_library")["n"] == 0
    import psycopg
    with pytest.raises(psycopg.errors.InsufficientPrivilege), transaction(source=True) as conn:
        conn.execute("SELECT * FROM research_question_library")


@pytest.mark.parametrize("value", ["  ", "ab", "x"*601, "abc\x00def", "abc\x1bdef"])
def test_invalid_question(value):
    with pytest.raises(ValidationError):
        library.SaveQuestion(question=value)


def test_unknown_company_does_not_create_question(owner):
    with pytest.raises(ValueError):
        library.save(owner, str(uuid4()), library.SaveQuestion(question="Can margins recover?"))


def test_api_requires_session_and_rejects_injected_owner(owner):
    from fastapi.testclient import TestClient
    from thesis.app import app
    client = TestClient(app)
    url = f"/api/v1/companies/{INSTRUMENT}/question-library"
    assert client.put(url, json={"question":"Can margins recover?"}).status_code == 401
    client.get("/api/v1/session")
    assert client.put(url, json={"question":"Can margins recover?"}).status_code == 403
    headers = {"X-Thesis-Request":"local-ui"}
    result = client.put(url, headers=headers, json={"question":"Can margins recover?"})
    assert result.status_code == 200
    assert result.json()["result"]["selected_question"] == "Can margins recover?"
    assert client.put(url, headers=headers, json={"question":"Can margins recover?", "owner_id":owner}).status_code == 422


def test_bundled_font_and_license_are_served_without_private_file_access():
    from fastapi.testclient import TestClient
    from thesis.app import app
    client = TestClient(app)
    font = client.get("/fonts/MiSansLatin-Regular.woff2")
    assert font.status_code == 200 and font.content[:4] == b"wOF2"
    license = client.get("/fonts/MiSans-license.pdf")
    assert license.status_code == 200 and license.content[:4] == b"%PDF"
    assert client.get("/fonts/%2e%2e/%2e%2e/.env").status_code == 404
