from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import secrets
import threading
import logging
from uuid import UUID
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from . import service
from .config import ROOT, DATA, OWNER
from .models import (
    SaveIdea,
    ResearchAction,
    ReviewAction,
    Advance,
    EvidenceReviewRequest,
    EventReviewRequest,
)


def session_token():
    path = DATA / "session.key"
    if not path.exists():
        path.write_text(secrets.token_urlsafe(32))
        path.chmod(0o600)
    return path.read_text().strip()


@asynccontextmanager
async def lifespan(app):
    stop = threading.Event()

    def loop():
        while not stop.wait(0.4):
            try:
                service.work_once()
            except Exception:
                logging.getLogger("thesis").exception("Recorded evaluation failed")

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()

    def watch_loop():
        from .monitoring.news_watch import run_once

        while not stop.wait(5):
            try:
                run_once(OWNER)
            except Exception:
                logging.getLogger("thesis").exception("Local research watch failed")

    watch_thread = threading.Thread(target=watch_loop, daemon=True)
    watch_thread.start()

    def filing_loop():
        from .monitoring.filing_watch import run_once

        while not stop.wait(5):
            try:
                run_once(OWNER)
            except Exception:
                logging.getLogger("thesis").exception("Local filing watch failed")

    filing_thread = threading.Thread(target=filing_loop, daemon=True)
    filing_thread.start()

    def review_loop():
        from .monitoring.review_schedule import run_once

        while not stop.wait(5):
            try:
                run_once(OWNER)
            except Exception:
                logging.getLogger("thesis").exception("Local weekly review failed")

    review_thread = threading.Thread(target=review_loop, daemon=True)
    review_thread.start()

    def telegram_loop():
        from .monitoring.telegram import run_once

        while not stop.wait(5):
            try:
                run_once(OWNER)
            except Exception:
                # Do not log external transport URLs, tokens or private messages.
                logging.getLogger("thesis").warning("Telegram delivery check failed")

    telegram_thread = threading.Thread(target=telegram_loop, daemon=True)
    telegram_thread.start()
    from .research import loading
    load_lease = loading.worker_lease()
    if load_lease is not None:
        loading.recover(OWNER)
    def load_loop():
        while not stop.wait(0.5):
            try:
                loading.work_once(OWNER)
            except Exception:
                logging.getLogger("thesis").warning("Research loading worker could not finish a step")
    load_threads = [threading.Thread(target=load_loop, daemon=True) for _ in range(4 if load_lease is not None else 0)]
    for worker in load_threads:
        worker.start()
    yield
    stop.set()
    thread.join(timeout=5)
    watch_thread.join(timeout=5)
    filing_thread.join(timeout=5)
    review_thread.join(timeout=5)
    telegram_thread.join(timeout=5)
    for worker in load_threads:
        worker.join(timeout=1)
    if load_lease is not None:
        load_lease.close()


app = FastAPI(
    title="Thesis local prototype", lifespan=lifespan, docs_url=None, redoc_url=None
)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
)


def error(status, message):
    return JSONResponse(
        status_code=status,
        content={
            "result": {
                "errors": [{"error_code": str(status), "error_message": message}]
            }
        },
    )


@app.middleware("http")
async def local_session(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        if origin and origin not in {f"http://{request.headers.get('host')}"}:
            return error(403, "Use this app from its local window.")
        if request.headers.get("sec-fetch-site") in {"cross-site", "same-site"}:
            return error(403, "Cross-origin requests are not accepted.")
        if request.url.path != "/api/v1/session" and not secrets.compare_digest(
            request.cookies.get("thesis_session", ""), session_token()
        ):
            return error(401, "Open the local app to start your demo session.")
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and request.headers.get("x-thesis-request") != "local-ui"
        ):
            return error(403, "A local app request is required.")
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    )
    response.headers["Cache-Control"] = (
        "no-store" if request.url.path.startswith("/api/") else "no-cache"
    )
    return response


@app.exception_handler(service.Conflict)
async def conflict_handler(request, exc):
    return error(409, str(exc))


@app.exception_handler(service.Missing)
async def missing_handler(request, exc):
    return error(404, str(exc))


@app.exception_handler(ValueError)
async def value_handler(request, exc):
    return error(422, str(exc))


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return error(422, "Check your question, conditions and numeric values.")


@app.get("/api/v1/session")
def bootstrap():
    from .db import transaction, one

    with transaction() as conn:
        preferred = one(
            conn,
            "SELECT instrument_id FROM market_quotes ORDER BY retrieved_at DESC LIMIT 1",
        )
    response = JSONResponse(
        {
            "result": {
                "mode": "local-pitch",
                "account": "Local demo",
                "preferred_instrument": (
                    str(preferred["instrument_id"]) if preferred else None
                ),
            }
        }
    )
    response.set_cookie(
        "thesis_session",
        session_token(),
        httponly=True,
        samesite="strict",
        max_age=86400,
    )
    return response


@app.get("/api/v1/workspace")
def workspace(instrument_id: UUID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")):
    result = service.state(OWNER, str(instrument_id))
    from .db import transaction, one
    with transaction() as conn:
        result["workspace_reset_at"] = one(conn, "SELECT reset_at FROM workspace_settings WHERE singleton")["reset_at"]
    return {"result": result}


@app.get("/api/v1/research-review")
def research_review(
    days: int = 7,
    cutoff: datetime | None = None,
    instrument_id: UUID | None = None,
    review: str = "all",
    page: int = 0,
):
    from .review_digest import prepare

    return {
        "result": prepare(
            OWNER,
            days=days,
            cutoff=cutoff,
            instrument_id=instrument_id,
            review=review,
            page=page,
        )
    }


@app.get("/api/v1/research-review/export")
def research_review_export(
    days: int = 7,
    cutoff: datetime | None = None,
    instrument_id: UUID | None = None,
    review: str = "all",
):
    from .review_digest import download

    name, html = download(
        OWNER, days=days, cutoff=cutoff, instrument_id=instrument_id, review=review
    )
    return HTMLResponse(
        html, headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


from .research import answers


@app.get("/api/v1/companies/{instrument_id}/discussion-themes")
def theme_history(
    instrument_id: UUID, analysis_id: UUID | None = None, before: UUID | None = None
):
    from .research import discussion_themes

    return {
        "result": discussion_themes.history(
            str(instrument_id),
            str(analysis_id) if analysis_id else None,
            str(before) if before else None,
        )
    }


@app.post("/api/v1/companies/{instrument_id}/sentiment/{analysis_id}/discussion-themes")
def theme_reading(instrument_id: UUID, analysis_id: UUID):
    from .research import discussion_themes

    return {"result": discussion_themes.generate(str(instrument_id), str(analysis_id))}


@app.get("/api/v1/companies/{instrument_id}/discussion-themes/{record_id}/export")
def theme_export(instrument_id: UUID, record_id: UUID):
    from .research import discussion_themes

    name, html = discussion_themes.download(str(instrument_id), str(record_id))
    return HTMLResponse(
        html, headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


@app.get("/api/v1/companies/{instrument_id}/expectations")
def expectation_history(instrument_id: UUID, before: UUID | None = None):
    from .research import expectations

    return {
        "result": expectations.history(
            str(instrument_id), str(before) if before else None
        )
    }


@app.post("/api/v1/companies/{instrument_id}/expectations")
def extract_expectations(instrument_id: UUID):
    from .research import expectations

    return {"result": expectations.generate(str(instrument_id))}


@app.get("/api/v1/companies/{instrument_id}/expectations/{record_id}/export")
def expectation_export(instrument_id: UUID, record_id: UUID):
    from .research import expectations

    name, html = expectations.download(str(instrument_id), str(record_id))
    return HTMLResponse(
        html, headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


@app.post("/api/v1/companies/{instrument_id}/questions")
def ask_research(instrument_id: UUID, payload: answers.Ask):
    return {"result": answers.generate(OWNER, str(instrument_id), payload)}


@app.get("/api/v1/companies/{instrument_id}/questions")
def research_questions(instrument_id: UUID, before: UUID | None = None):
    return {"result": answers.history(OWNER, str(instrument_id), before)}


from .research import question_library


@app.put("/api/v1/companies/{instrument_id}/question-library")
def save_research_question(instrument_id: UUID, payload: question_library.SaveQuestion):
    return {"result": question_library.save(OWNER, str(instrument_id), payload)}


@app.get("/api/v1/research-answers/{answer_id}")
def research_answer(answer_id: UUID):
    return {"result": answers.get(OWNER, str(answer_id))}


@app.get("/api/v1/research-answers/{answer_id}/export")
def research_answer_export(answer_id: UUID):
    name, html = answers.download(OWNER, str(answer_id))
    return HTMLResponse(
        html, headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


from .valuation import ScenarioRequest, SaveScenario


@app.get("/api/v1/companies/{instrument_id}/valuation")
def valuation_context(instrument_id: UUID):
    from .valuation import context

    return {"result": context(OWNER, str(instrument_id))}


@app.post("/api/v1/companies/{instrument_id}/multiples/refresh")
def refresh_multiples(instrument_id: UUID):
    from .research.multiples import refresh

    return {"result": refresh(str(instrument_id))}


@app.post("/api/v1/valuation/preview")
def valuation_preview(payload: ScenarioRequest):
    from .valuation import preview

    return {"result": preview(OWNER, payload)}


@app.post("/api/v1/companies/{instrument_id}/analyst-targets/refresh")
def refresh_analyst_targets(instrument_id: UUID):
    from .research.analyst_targets import refresh

    return {"result": refresh(str(instrument_id))}


@app.post("/api/v1/valuation/save")
def valuation_save(payload: SaveScenario):
    from .valuation import save

    return {"result": save(OWNER, payload)}


@app.get("/api/v1/valuations/{scenario_id}")
def valuation_record(scenario_id: UUID):
    from .valuation import get

    return {"result": get(OWNER, str(scenario_id))}


@app.get("/api/v1/valuations/{scenario_id}/export")
def valuation_export(scenario_id: UUID):
    from .valuation import download

    name, html = download(OWNER, str(scenario_id))
    return HTMLResponse(
        html, headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


@app.post("/api/v1/idea")
def save(payload: SaveIdea):
    return {"result": service.save_idea(OWNER, payload)}


@app.post("/api/v1/research-actions")
def research(payload: ResearchAction):
    service.research_action(OWNER, payload)
    return {"result": {"saved": True}}


@app.post("/api/v1/evaluations/{evaluation_id}/review")
def review(evaluation_id: UUID, payload: ReviewAction):
    return {"result": service.review(OWNER, evaluation_id, payload.action)}


@app.post("/api/v1/demo/advance")
def advance(payload: Advance):
    return {
        "result": service.advance(
            OWNER, payload.expected_stage, str(payload.instrument_id)
        )
    }


from pydantic import BaseModel, ConfigDict, field_validator
from typing import Literal


class WatchSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool
    interval_minutes: Literal[60, 240] = 60
    match_idea: bool | None = None
    include_context: bool | None = None
    idea_purpose: Literal["reasoning", "question"] | None = None


class ReviewScheduleSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool
    weekday: int
    minute_of_day: int
    time_zone: str


@app.get("/api/v1/scheduled-reviews")
def saved_review_history(before: UUID | None = None):
    from .monitoring import review_schedule

    return {"result": review_schedule.history(OWNER, before=before)}


@app.post("/api/v1/review-schedule")
def configure_review_schedule(payload: ReviewScheduleSettings):
    from .monitoring import review_schedule

    return {"result": review_schedule.configure(OWNER, **payload.model_dump())}


@app.get("/api/v1/scheduled-reviews/{review_id}")
def saved_review(review_id: UUID, page: int = 0):
    from .monitoring import review_schedule

    return {"result": review_schedule.read(OWNER, review_id, page=page)}


@app.get("/api/v1/scheduled-reviews/{review_id}/export")
def saved_review_export(review_id: UUID):
    from .monitoring import review_schedule

    name, html = review_schedule.download(OWNER, review_id)
    return HTMLResponse(
        html, headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


@app.post("/api/v1/scheduled-reviews/{review_id}/seen")
def saved_review_seen(review_id: UUID):
    from .monitoring import review_schedule

    return {"result": review_schedule.mark_seen(OWNER, review_id)}


@app.post("/api/v1/social/refresh")
def refresh_social():
    from .research.social import refresh

    return {"result": refresh()}


@app.post("/api/v1/companies/{instrument_id}/social/refresh")
def refresh_company_social(instrument_id: UUID):
    from .research.social import refresh_company

    return {"result": refresh_company(str(instrument_id))}


@app.get("/api/v1/companies/{instrument_id}/watch-checks")
def watch_checks(instrument_id: UUID, before: UUID | None = None):
    from .monitoring.watch_history import history

    return {"result": history(OWNER, str(instrument_id), before)}


@app.get("/api/v1/social-sources/{post_id}/conversation")
def saved_conversation(post_id: UUID):
    from .research.conversation import read

    return {"result": read(str(post_id))}


@app.post("/api/v1/social-sources/{post_id}/conversation")
def collect_conversation(post_id: UUID):
    from .research.conversation import collect

    return {"result": collect(str(post_id))}


@app.post("/api/v1/companies/{instrument_id}/sentiment")
def analyze_sentiment(instrument_id: UUID):
    from .research.sentiment import generate
    from .monitoring.news_watch import publish

    result = generate(str(instrument_id))
    publish(OWNER, str(instrument_id), result["id"])
    return {"result": result}


@app.get("/api/v1/companies/{instrument_id}/sentiment-history")
def sentiment_history(instrument_id: UUID, before: UUID | None = None):
    from .research.sentiment_history import history

    return {"result": history(str(instrument_id), before)}


@app.get("/api/v1/companies/{instrument_id}/sentiment-comparison")
def sentiment_comparison(instrument_id: UUID, before: UUID, after: UUID):
    from .research.sentiment_history import compare

    return {"result": compare(str(instrument_id), str(before), str(after))}


@app.post("/api/v1/companies/{instrument_id}/news-watch")
def configure_watch(instrument_id: UUID, payload: WatchSettings):
    from .monitoring.news_watch import configure

    return {
        "result": configure(
            OWNER,
            str(instrument_id),
            payload.enabled,
            payload.interval_minutes,
            match_idea=payload.match_idea,
            include_context=payload.include_context,
            idea_purpose=payload.idea_purpose,
        )
    }


@app.post("/api/v1/research-alerts/{alert_id}/review")
def review_research_alert(alert_id: UUID, payload: ReviewAction):
    from .monitoring.news_watch import review

    return {"result": review(OWNER, str(alert_id), payload.action)}


class EventWatchSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: UUID | None


@app.post("/api/v1/companies/{instrument_id}/event-watch")
def configure_event_watch(instrument_id: UUID, payload: EventWatchSettings):
    from .monitoring.event_watch import configure

    return {
        "result": configure(
            OWNER,
            str(instrument_id),
            str(payload.version_id) if payload.version_id else None,
        )
    }


class IdeaAlertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_id: UUID
    version_id: UUID
    purpose: Literal["reasoning", "question"] = "reasoning"


@app.post("/api/v1/companies/{instrument_id}/idea-alert-check")
def check_idea_sources(instrument_id: UUID, payload: IdeaAlertRequest):
    from .research.idea_alerts import generate

    return {
        "result": generate(
            OWNER,
            str(instrument_id),
            str(payload.analysis_id),
            str(payload.version_id),
            purpose=payload.purpose,
        )
    }


@app.post("/api/v1/idea-alerts/{check_id}/review")
def review_idea_alert(check_id: UUID, payload: ReviewAction):
    from .research.idea_alerts import review

    return {"result": review(OWNER, str(check_id), payload.action)}


@app.get("/api/v1/idea-alerts/{check_id}/export")
def export_idea_alert(check_id: UUID):
    from .research.idea_alerts import download

    filename, content = download(OWNER, str(check_id))
    return HTMLResponse(
        content, headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/v1/model-status")
def model_status():
    from .providers.ledger import snapshot
    from .providers.settings import live_key, REASONING_MODEL

    try:
        live_key()
        enabled = True
    except ValueError:
        enabled = False
    try:
        live_key(REASONING_MODEL)
        comparison_enabled = True
    except ValueError:
        comparison_enabled = False
    return {
        "result": dict(
            enabled=enabled,
            comparison_enabled=comparison_enabled,
            briefing_enabled=comparison_enabled,
            budget=snapshot(),
        )
    }


@app.post("/api/v1/research/selection")
def select_research(payload: Advance):
    return {
        "result": service.research_selection(
            payload.expected_stage, str(payload.instrument_id)
        )
    }


from pydantic import BaseModel, ConfigDict
from typing import Literal


class SecCompany(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str

    @field_validator("symbol")
    @classmethod
    def supported_symbol(cls, value):
        from .research.directory import valid_symbol

        value = value.strip().upper()
        if not valid_symbol(value):
            raise ValueError("Choose a US ticker from the company search.")
        return value


@app.get("/api/v1/company-directory")
def company_directory(q: str = ""):
    from .research.directory import search
    return {"result": search(q)}


@app.post("/api/v1/company-directory/refresh")
def refresh_company_directory():
    from .research.directory import refresh
    return {"result": refresh()}


@app.post("/api/v1/sec/companies")
def add_sec_company(payload: SecCompany):
    from .research.sec.service import add_company

    return {"result": add_company(payload.symbol)}


@app.post("/api/v1/sec/{instrument_id}/refresh")
def refresh_sec_company(instrument_id: UUID):
    from .research.sec.service import refresh

    result = refresh(str(instrument_id))
    service.queue_current(OWNER)
    return {"result": result}


class FilingWatchSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool


@app.post("/api/v1/companies/{instrument_id}/filing-watch")
def configure_filing_watch(instrument_id: UUID, payload: FilingWatchSettings):
    from .monitoring.filing_watch import configure

    return {"result": configure(OWNER, str(instrument_id), payload.enabled)}


@app.get("/api/v1/companies/{instrument_id}/filing-checks")
def filing_checks(instrument_id: UUID, before: UUID | None = None):
    from .monitoring.filing_watch import history

    return {"result": history(OWNER, str(instrument_id), before)}


@app.get("/api/v1/companies/{instrument_id}/price-history")
def price_history(instrument_id: UUID):
    from .research.price_history import present

    return {"result": present(str(instrument_id))}


@app.post("/api/v1/companies/{instrument_id}/price-history/refresh")
def refresh_price_history(instrument_id: UUID):
    from .research.price_history import refresh

    return {"result": refresh(str(instrument_id))}


@app.post("/api/v1/market/{instrument_id}/refresh")
def refresh_market(instrument_id: UUID):
    from .research.market import refresh

    result = refresh(str(instrument_id))
    service.queue_current(OWNER)
    return {"result": result}


@app.post("/api/v1/market/{instrument_id}/brief")
def market_brief(instrument_id: UUID):
    from .research.market_brief import generate

    return {"result": generate(str(instrument_id))}


@app.post("/api/v1/ideas/versions/{version_id}/evidence-review")
def idea_evidence_review(version_id: UUID, payload: EvidenceReviewRequest):
    from .research.idea_review import generate

    return {
        "result": generate(
            OWNER,
            str(version_id),
            payload.snapshot_id,
            str(payload.evaluation_id) if payload.evaluation_id else None,
        )
    }


@app.post("/api/v1/ideas/versions/{version_id}/event-review")
def event_evidence_review(version_id: UUID, payload: EventReviewRequest):
    if payload.evaluation_id:
        raise ValueError("Event checks use a saved revision and source snapshot.")
    from .research.event_review import generate

    return {
        "result": generate(
            OWNER,
            str(version_id),
            payload.snapshot_id,
            event_periods=payload.event_periods,
        )
    }


@app.get("/api/v1/ideas/versions/{version_id}/review-export")
def review_export(
    version_id: UUID,
    evaluation_id: UUID | None = None,
    comparison_id: UUID | None = None,
    event_review_id: UUID | None = None,
):
    from .review_export import download

    filename, content = download(
        OWNER,
        str(version_id),
        evaluation_id=evaluation_id,
        comparison_id=comparison_id,
        event_review_id=event_review_id,
    )
    return HTMLResponse(
        content, headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


from .research.proposals import GenerateRequest
from pydantic import BaseModel, ConfigDict, Field


class ApproveSuggestions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposal_ids: list[UUID] = Field(min_length=1, max_length=3)
    definition: SaveIdea


@app.post("/api/v1/proposals/approve")
def approve_suggestions(payload: ApproveSuggestions):
    from .research.proposals import decide_many

    return {
        "result": decide_many(
            OWNER, payload.proposal_ids, definition=payload.definition
        )
    }


@app.post("/api/v1/proposals/generate")
def generate_proposals(payload: GenerateRequest):
    from .research.proposals import generate

    return {"result": generate(OWNER, payload)}


@app.post("/api/v1/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: UUID, payload: SaveIdea):
    from .research.proposals import decide

    return {"result": decide(OWNER, str(proposal_id), definition=payload)}


@app.post("/api/v1/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: UUID):
    from .research.proposals import decide

    return {"result": decide(OWNER, str(proposal_id))}


class TelegramDeliverySetting(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool


@app.get("/api/v1/telegram")
def telegram_status():
    from .monitoring import telegram
    return {"result": telegram.status(OWNER)}


@app.post("/api/v1/telegram/connect")
def telegram_connect():
    from .monitoring import telegram
    return {"result": telegram.connect(OWNER)}


@app.post("/api/v1/telegram/check")
def telegram_check():
    from .monitoring import telegram
    return {"result": telegram.check_connection(OWNER)}


@app.post("/api/v1/telegram/delivery")
def telegram_delivery(payload: TelegramDeliverySetting):
    from .monitoring import telegram
    return {"result": telegram.configure(OWNER, payload.enabled)}


@app.post("/api/v1/telegram/disconnect")
def telegram_disconnect():
    from .monitoring import telegram
    return {"result": telegram.disconnect(OWNER)}


@app.post("/api/v1/telegram/test")
def telegram_test():
    from .monitoring import telegram
    return {"result": telegram.test_message(OWNER)}


dist = ROOT / "frontend" / "dist"
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    if (dist / "fonts").exists():
        app.mount("/fonts", StaticFiles(directory=dist / "fonts"), name="fonts")


@app.get("/")
def index():
    return FileResponse(dist / "index.html")


class ResearchLoadSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    initial: bool = False
    analyze: bool = False
    lookback_days: Literal[1, 7, 30] = 7


@app.get("/api/v1/companies/{instrument_id}/loading")
def research_loading(instrument_id: UUID):
    from .research.loading import latest
    return {"result": latest(OWNER, str(instrument_id))}


@app.post("/api/v1/companies/{instrument_id}/loading")
def start_research_loading(instrument_id: UUID, payload: ResearchLoadSettings):
    from .research.loading import start
    return {"result": start(OWNER, str(instrument_id), **payload.model_dump())}
