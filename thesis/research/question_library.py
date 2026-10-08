"""Owner/company-scoped question bookmarks; no model or monitoring side effects."""
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, field_validator
from ..db import transaction, one, rows


class SaveQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str = Field(min_length=3, max_length=600)

    @field_validator("question")
    @classmethod
    def clean(cls, value):
        if any(ord(c) < 32 and c not in "\n\t" for c in value):
            raise ValueError("Enter a clear research question.")
        value = " ".join(value.split())
        if len(value) < 3:
            raise ValueError("Enter a question of 3–600 characters.")
        return value


def present(conn, owner, instrument_id):
    items = rows(conn, "SELECT id,question,selected,created_at FROM research_question_library WHERE owner_id=%s AND instrument_id=%s ORDER BY created_at,id", (owner,instrument_id))
    return dict(items=items, selected_question=next((i["question"] for i in items if i["selected"]), None))


def save(owner, instrument_id, payload):
    with transaction(owner) as conn:
        if not one(conn, "SELECT id FROM instruments WHERE id=%s", (instrument_id,)):
            raise ValueError("Choose a company before adding a question.")
        # Serialize selection and deduplication, including the first two concurrent adds.
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"question-library:{owner}:{instrument_id}",))
        conn.execute("UPDATE research_question_library SET selected=false WHERE owner_id=%s AND instrument_id=%s AND selected", (owner,instrument_id))
        conn.execute("INSERT INTO research_question_library(id,owner_id,instrument_id,question,question_key,selected) VALUES(%s,%s,%s,%s,%s,true) ON CONFLICT(owner_id,instrument_id,question_key) DO UPDATE SET selected=true", (str(uuid4()),owner,instrument_id,payload.question,payload.question.casefold()))
        return present(conn, owner, instrument_id)
