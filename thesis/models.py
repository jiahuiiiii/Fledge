from decimal import Decimal
from datetime import date
from typing import Literal, Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Condition(Strict):
    condition_id: UUID
    role: Literal["required", "risk"] = "required"
    metric: Literal["revenue_growth", "operating_margin"]
    operator: Literal[">=", "<="] = ">="
    threshold: Decimal = Field(ge=-100, le=1000, allow_inf_nan=False)
    unit: Literal["percent"] = "percent"
    basis: Literal["reported"] = "reported"
    period_type: Literal["quarter", "annual"] = "quarter"
    max_report_age_days: int | None = Field(default=None, ge=1, le=3650, strict=True)

    expected_period_end: date | None = None
    expected_report_by: date | None = None

    @model_validator(mode="after")
    def expected_reporting_dates(self):
        start, due = self.expected_period_end, self.expected_report_by
        if (start is None) != (due is None):
            raise ValueError(
                "Choose both the required period end and expected-by date, or clear both."
            )
        if start is not None and (
            due < start or due == date.max or (due - start).days > 3650
        ):
            raise ValueError(
                "Use an expected-by date on or after the period end, within 3650 days."
            )
        return self


class EventCondition(Strict):
    condition_id: UUID
    description: str = Field(min_length=5, max_length=400)
    evidence_requirement: str = Field(min_length=5, max_length=600)
    role: Literal["required", "risk"] = "required"
    date_basis: Literal["report_publication", "event_occurrence"] = "report_publication"
    repeat_months: int = Field(default=0, strict=True)
    repeat_count: int = Field(default=1, ge=1, le=12, strict=True)
    window_start: date
    deadline: date

    @field_validator("description", "evidence_requirement")
    @classmethod
    def substantive_text(cls, value):
        if len(value.strip()) < 5:
            raise ValueError("Describe the event and evidence you need.")
        return value.strip()

    @model_validator(mode="after")
    def ordered_window(self):
        if (
            self.deadline < self.window_start
            or self.deadline == date.max
            or (self.deadline - self.window_start).days > 3650
        ):
            raise ValueError("Use an ordered event window of at most ten years.")
        from .monitoring.event_windows import windows

        windows(self.model_dump())
        return self


class SaveIdea(Strict):
    instrument_id: UUID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    expected_revision: int = Field(ge=0)
    question: str = Field(min_length=1, max_length=200)
    reasoning: str = Field(max_length=3000)
    status: Literal["draft", "monitoring", "archived"]
    conditions: list[Condition] = Field(max_length=4)
    events: list[EventCondition] = Field(default_factory=list, max_length=3)

    @field_validator("question")
    @classmethod
    def trim_question(cls, v):
        if not v.strip():
            raise ValueError("Choose a question")
        return v.strip()


class ResearchAction(Strict):
    instrument_id: UUID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    question: str = Field(min_length=1, max_length=200)
    action: Literal["investigate", "unresolved", "reject"]


class ReviewAction(Strict):
    action: Literal["reviewed", "unresolved"]


class Advance(Strict):
    instrument_id: UUID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    expected_stage: int = Field(ge=0, le=4)


class EvidenceReviewRequest(Strict):
    snapshot_id: int = Field(gt=0, strict=True)
    evaluation_id: UUID | None = None


class EventReviewRequest(EvidenceReviewRequest):
    event_periods: (
        dict[UUID, Annotated[int, Field(ge=1, le=12, strict=True)]] | None
    ) = Field(default=None, max_length=3)
