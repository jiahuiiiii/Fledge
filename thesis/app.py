from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import secrets
import threading
import logging
import os
import re
from uuid import UUID
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware
from . import service
from . import auth
from . import wake
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
    from .runtime_status import record_start
    try:
        record_start()
    except OSError:
        logging.getLogger('thesis').warning('Startup source record unavailable; running version is unverified.')
    stop = threading.Event()

    def loop():
        while not stop.wait(0.4):
            try:
                for owner in auth.background_owners():
                    service.work_once(owner)
            except Exception:
                logging.getLogger("thesis").exception("Recorded evaluation failed")

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()

    def watch_loop(lane=None):
        from .monitoring.news_watch import run_once

        while not stop.wait(5):
            # A few seconds of Power Nap is too short for a check; wait until awake.
            if not wake.settled():
                continue
            try:
                for owner in auth.background_owners():
                    run_once(owner, lane=lane)
            except Exception:
                logging.getLogger("thesis").exception("Local research watch failed")

    # Two workers: different companies' scheduled checks no longer queue behind
    # each other. Each claims a different watch through its lease.
    watch_threads = [threading.Thread(target=watch_loop, daemon=True) for _ in range(2)]
    watch_threads += [threading.Thread(target=watch_loop, args=("fast",), daemon=True) for _ in range(2)]
    for watch_thread in watch_threads:
        watch_thread.start()

    def move_loop():
        from .monitoring.move_watch import run_once
        while not stop.wait(5):
            if not wake.settled():
                continue
            try:
                for owner in auth.background_owners():
                    run_once(owner)
            except Exception:
                logging.getLogger("thesis").warning("Price preview check failed")

    move_thread = threading.Thread(target=move_loop, daemon=True)
    move_thread.start()

    def filing_loop():
        from .monitoring.filing_watch import run_once

        while not stop.wait(5):
            if not wake.settled():
                continue
            try:
                for owner in auth.background_owners():
                    run_once(owner)
            except Exception:
                logging.getLogger("thesis").exception("Local filing watch failed")

    filing_thread = threading.Thread(target=filing_loop, daemon=True)
    filing_thread.start()

    def review_loop():
        from .monitoring.review_schedule import run_once

        while not stop.wait(5):
            try:
                for owner in auth.background_owners():
                    run_once(owner)
            except Exception:
                logging.getLogger("thesis").exception("Local weekly review failed")

    review_thread = threading.Thread(target=review_loop, daemon=True)
    review_thread.start()

    def telegram_loop():
        from .monitoring.telegram import run_once
        from .monitoring.alert_routing import poll_preview as preview_routes
        from .monitoring.daily_updates import poll as prepare_daily_updates

        backoff = wake.Backoff(5, name="Telegram delivery check", ceiling=120)
        while not stop.wait(backoff.delay()):
            if not wake.settled():
                continue
            try:
                for owner in auth.background_owners():
                    preview_routes(owner)
                    prepare_daily_updates(owner)
                    run_once(owner)
            except Exception as exc:
                # Do not log external transport URLs, tokens or private messages.
                backoff.failed(exc)
            else:
                backoff.succeeded()

    telegram_thread = threading.Thread(target=telegram_loop, daemon=True)

    # Rating taps get their own quick loop so a slow send never delays a confirmation.
    def feedback_loop():
        from .monitoring.telegram_updates import poll_feedback, POLL_SECONDS

        # Telegram keeps taps for 24 hours, so pausing during an outage loses none.
        backoff = wake.Backoff(POLL_SECONDS, name="Telegram rating check")
        while not stop.wait(backoff.delay()):
            if not wake.settled():
                continue
            try:
                poll_feedback()
            except Exception as exc:
                backoff.failed(exc)
            else:
                backoff.succeeded()

    feedback_thread = threading.Thread(target=feedback_loop, daemon=True)
    feedback_thread.start()
    telegram_thread.start()
    from .research import loading
    load_lease = loading.WorkerLease(auth.background_owners)

    def load_loop():
        while not stop.wait(0.5):
            try:
                if not load_lease.held():
                    continue
                for owner in auth.background_owners():
                    loading.work_once(owner)
            except Exception:
                logging.getLogger("thesis").warning("Research loading worker could not finish a step")

    load_threads = [threading.Thread(target=load_loop, daemon=True) for _ in range(4)]
    for worker in load_threads:
        worker.start()

    def warm_financials():
        # Read-only: fill the parsed-filing caches so the first Financials open
        # after a restart is not slow. Access checks still run on every real read.
        from .db import transaction, rows
        from .research.sec.financial_story import present as financial_story

        if stop.wait(3):
            return
        try:
            owner = next(iter(auth.background_owners()), None)
            if owner is None:
                return
            with transaction(owner) as conn:
                companies = [str(r["instrument_id"]) for r in rows(conn,
                    "SELECT DISTINCT instrument_id FROM disclosure_documents WHERE source_id='sec-disclosures'")]
            for iid in companies:
                if stop.is_set():
                    return
                service.financial_workspace(owner, iid)
                with transaction(owner, consistent=True) as conn:
                    financial_story(conn, iid)
        except Exception:
            logging.getLogger("thesis").warning("Financial cache warm-up stopped early")

    if os.environ.get("THESIS_TEST_OFFLINE") != "true":
        threading.Thread(target=warm_financials, daemon=True).start()
    yield
    stop.set()
    thread.join(timeout=5)
    for watch_thread in watch_threads:
        watch_thread.join(timeout=5)
    move_thread.join(timeout=5)
    filing_thread.join(timeout=5)
    review_thread.join(timeout=5)
    telegram_thread.join(timeout=5)
    feedback_thread.join(timeout=5)
    for worker in load_threads:
        worker.join(timeout=1)
    load_lease.close()


app = FastAPI(
    title="Fledge local prototype", lifespan=lifespan, docs_url=None, redoc_url=None
)


def public_origin():
    """THESIS_PUBLIC_ORIGIN (e.g. https://fledge.example.com) when Fledge is
    served on the internet behind an HTTPS front door; empty on a laptop."""
    from .providers.settings import settings
    if os.environ.get("THESIS_TEST_OFFLINE") == "true":
        return os.environ.get("THESIS_PUBLIC_ORIGIN", "").rstrip("/")
    return (settings().get("THESIS_PUBLIC_ORIGIN") or "").strip().rstrip("/")


def allowed_hosts():
    hosts = ["127.0.0.1", "localhost", "testserver"]
    origin = public_origin()
    if origin:
        from urllib.parse import urlsplit
        host = urlsplit(origin).hostname
        if host:
            hosts.append(host)
    return hosts


app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())


def error(status, message):
    return JSONResponse(
        status_code=status,
        content={
            "result": {
                "errors": [{"error_code": str(status), "error_message": message}]
            }
        },
    )


def cookie_options(max_age):
    # Over HTTPS the browser must never send the session over plain HTTP.
    return dict(httponly=True, samesite="strict", max_age=max_age,
                secure=public_origin().startswith("https://"))


@app.middleware("http")
async def local_session(request: Request, call_next):
    owner = None
    if request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        allowed = {f"http://{request.headers.get('host')}"}
        if public_origin():
            allowed.add(public_origin())
        if origin and origin not in allowed:
            return error(403, "Use this app from its local window.")
        if request.headers.get("sec-fetch-site") in {"cross-site", "same-site"}:
            return error(403, "Cross-origin requests are not accepted.")
        public = request.url.path in {"/api/v1/session", "/api/v1/auth/login", "/api/v1/auth/logout", "/api/v1/auth/register", "/api/v1/auth/password-login", "/api/v1/auth/password-reset", "/api/v1/legal"}
        try:
            managed = auth.configuration()
            if managed:
                cookie = request.cookies.get(auth.COOKIE, "")
                if not public or (request.url.path == "/api/v1/session" and cookie) or (request.url.path == "/api/v1/auth/logout" and request.headers.get('x-thesis-account')):
                    try:
                        owner = await run_in_threadpool(auth.authenticate, cookie)
                    except auth.AuthFailure as failure:
                        if not public or failure.status != 401:
                            return error(failure.status, str(failure))
            else:
                owner = OWNER
                if not public and not secrets.compare_digest(request.cookies.get(auth.COOKIE, ""), session_token()):
                    return error(401, "Open the local app to start your demo session.")
            expected=request.headers.get('x-thesis-account')
            if owner and expected and expected!=str(owner):
                response=error(409,'The signed-in account changed. Reloading its private workspace; your last action was not submitted.')
                response.headers['X-Thesis-Account']=str(owner)
                return response
        except auth.AuthFailure as failure:
            return error(failure.status, str(failure))
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and request.headers.get("x-thesis-request") != "local-ui"
        ):
            return error(403, "A local app request is required.")
    context = auth.account_context.set(owner)
    try:
        response = await call_next(request)
    finally:
        auth.account_context.reset(context)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if owner:response.headers['X-Thesis-Account']=str(owner)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data: https://financialmodelingprep.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    )
    response.headers["Cache-Control"] = cache_policy(request.url.path, response.status_code)
    return response


def cache_policy(path, status):
    """API answers are private and never stored. Built files under /assets
    have content hashes in their names, so a browser may keep them for good;
    fonts keep for a week; pages and anything else revalidate every time."""
    if path.startswith(("/api/", "/auth/")):
        return "no-store"
    if status in (200, 304) and path.startswith("/assets/"):
        return "public, max-age=31536000, immutable"
    if status in (200, 304) and path.startswith("/fonts/"):
        return "public, max-age=604800"
    return "no-cache"


# Outermost, so pages, built files and JSON answers over 1 KB are compressed
# with the headers above already set. Event streams are left uncompressed.
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.exception_handler(service.Conflict)
async def conflict_handler(request, exc):
    return error(409, str(exc))


@app.exception_handler(auth.AuthFailure)
async def auth_handler(request, exc):
    response=error(exc.status, str(exc))
    if exc.retry_after is not None:response.headers['Retry-After']=str(exc.retry_after)
    return response


@app.exception_handler(service.Missing)
async def missing_handler(request, exc):
    return error(404, str(exc))


@app.exception_handler(ValueError)
async def value_handler(request, exc):
    return error(422, str(exc))


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return error(422, "Check your question, conditions and numeric values.")


def terms_state(owner):
    from . import terms
    return terms.status(owner)


@app.get("/api/v1/session")
def bootstrap():
    from .db import transaction, one

    managed = auth.configuration()
    owner = auth.account_context.get()
    password_mode = bool(managed and managed.get("mode") == "password")
    if managed and not owner:
        response = JSONResponse({"result": {"mode": "password" if password_mode else "managed", "authenticated": False}})
        response.delete_cookie(auth.COOKIE)
        return response
    with transaction() as conn:
        preferred = one(
            conn,
            "SELECT instrument_id FROM market_quotes ORDER BY retrieved_at DESC LIMIT 1",
        )
    email=None
    username=None
    has_recovery=None
    if password_mode:
        from . import password_auth
        username=password_auth.username(owner)
        has_recovery=password_auth.has_recovery(owner) if username else None
    elif managed:
        with transaction(admin=True,consistent=True) as conn:
            identity=one(conn,'SELECT verified_email FROM auth_identities WHERE account_id=%s AND project_url=%s',(owner,managed['url']))
            email=identity['verified_email'] if identity else None
    response = JSONResponse(
        {
            "result": {
                "mode": "password" if password_mode else "managed" if managed else "local-pitch",
                "username": username,
                "has_recovery_code": has_recovery,
                "authenticated": True,
                "account": "Research account" if managed else "Local demo",
                "account_id": owner,
                "email": email,
                "is_installation_owner": owner == OWNER,
                "terms": terms_state(owner) if managed else None,
                "preferred_instrument": (
                    str(preferred["instrument_id"]) if preferred else None
                ),
            }
        }
    )
    if not managed:
        response.set_cookie(auth.COOKIE, session_token(), **cookie_options(86400))
    return response


from pydantic import BaseModel, Field, ConfigDict


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest):
    token = auth.send_link(payload.email)
    response = JSONResponse({"result": {"message": "Open the newest sign-in email in this browser. The link works once.", "retry_after": 60}})
    response.set_cookie(auth.FLOW_COOKIE, token, httponly=True, samesite="lax", max_age=900, path="/auth/callback")
    return response


class PasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(PasswordRequest):
    accept_terms: bool = False
    terms_version: str = Field(default="", max_length=16)


class TermsAcceptance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    terms_version: str = Field(min_length=1, max_length=16)


def password_session(action, payload):
    from . import password_auth
    config = auth.configuration()
    if not config or config.get("mode") != "password":
        return error(409, "Username sign-in is not enabled for this installation.")
    code = None
    try:
        if action == "register":
            from . import terms
            if not payload.accept_terms or payload.terms_version != terms.VERSION:
                return error(422, "Read and accept the Terms of Use and Privacy Notice to create an account.")
            cookie, lifetime, code = password_auth.register(payload.username, payload.password,
                                                            terms_version=terms.VERSION)
        elif action == "reset":
            cookie, lifetime, code = password_auth.reset_with_code(
                payload.username, payload.recovery_code, payload.password)
        else:
            cookie, lifetime = password_auth.login(payload.username, payload.password)
    except password_auth.PasswordFailure as failure:
        response = error(failure.status, str(failure))
        if failure.retry_after:
            response.headers["Retry-After"] = str(failure.retry_after)
        return response
    # The recovery code is returned once, only to the browser that just proved
    # it may have it, and is never stored in readable form.
    response = JSONResponse({"result": {"signed_in": True, "recovery_code": code}})
    response.set_cookie(auth.COOKIE, cookie, **cookie_options(lifetime))
    return response


class ResetRequest(PasswordRequest):
    recovery_code: str = Field(min_length=1, max_length=40)


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(default="", max_length=256)


@app.post("/api/v1/auth/password-reset")
def password_reset(payload: ResetRequest):
    return password_session("reset", payload)


def account_security(action, payload):
    from . import password_auth
    config = auth.configuration()
    if not config or config.get("mode") != "password":
        return error(409, "Username sign-in is not enabled for this installation.")
    owner = auth.current_owner()
    try:
        if action == "password":
            cookie, lifetime = password_auth.change_password(owner, payload.current_password, payload.new_password)
            response = JSONResponse({"result": {"changed": True}})
            response.set_cookie(auth.COOKIE, cookie, **cookie_options(lifetime))
            return response
        code = password_auth.replace_recovery_code(owner, payload.current_password)
        return {"result": {"recovery_code": code}}
    except password_auth.PasswordFailure as failure:
        response = error(failure.status, str(failure))
        if failure.retry_after:
            response.headers["Retry-After"] = str(failure.retry_after)
        return response


@app.post("/api/v1/account/password")
def change_password(payload: PasswordChange):
    return account_security("password", payload)


@app.post("/api/v1/account/recovery-code")
def new_recovery_code(payload: PasswordChange):
    return account_security("recovery", payload)


@app.get("/api/v1/legal")
def legal_contact():
    """Who people write to about their personal data (PDPA). Set per
    installation with THESIS_PRIVACY_CONTACT; readable before sign-in."""
    from .providers.settings import settings
    if os.environ.get("THESIS_TEST_OFFLINE") == "true":
        value = os.environ.get("THESIS_PRIVACY_CONTACT", "")
    else:
        value = settings().get("THESIS_PRIVACY_CONTACT") or ""
    value = value.strip()
    return {"result": {"privacy_contact": value if re.fullmatch(r"[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}", value) else ""}}


@app.post("/api/v1/auth/register")
def register_account(payload: RegisterRequest):
    return password_session("register", payload)


@app.post("/api/v1/terms/accept")
def accept_terms(payload: TermsAcceptance):
    from . import terms
    try:
        return {"result": terms.accept(auth.current_owner(), payload.terms_version)}
    except ValueError as failure:
        return error(422, str(failure))


@app.post("/api/v1/auth/password-login")
def password_login(payload: PasswordRequest):
    return password_session("login", payload)


@app.get("/auth/callback")
def login_callback(request: Request, code: str | None = None):
    try:
        token, lifetime = auth.complete(code, request.cookies.get(auth.FLOW_COOKIE))
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(auth.COOKIE, token, **cookie_options(lifetime))
    except auth.AuthFailure:
        response = RedirectResponse("/?auth_error=link", status_code=303)
    response.delete_cookie(auth.FLOW_COOKIE, path="/auth/callback")
    return response


@app.post("/api/v1/auth/logout")
def logout(request: Request):
    auth.logout(request.cookies.get(auth.COOKIE))
    response = JSONResponse({"result": {"signed_out": True}})
    response.delete_cookie(auth.COOKIE)
    response.delete_cookie(auth.FLOW_COOKIE, path="/auth/callback")
    return response


class InvestorProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    experience: str = Field(max_length=16)
    interests: list[str] = Field(default_factory=list, max_length=9)
    horizon: str | None = Field(default=None, max_length=16)
    goal: str = Field(max_length=16)
    detail_mode: str | None = Field(default=None, max_length=16)
    trade_frequency: str | None = Field(default=None, max_length=16)
    drop_reaction: str | None = Field(default=None, max_length=16)


class DetailMode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    detail_mode: str = Field(max_length=16)


class WatchlistCompany(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instrument_id: UUID


@app.get("/api/v1/profile")
def investor_profile():
    from . import profile
    return {"result": profile.get(auth.current_owner())}


@app.put("/api/v1/profile")
def save_investor_profile(payload: InvestorProfile):
    from . import profile
    return {"result": profile.save(auth.current_owner(), **payload.model_dump())}


@app.put("/api/v1/profile/detail-mode")
def save_detail_mode(payload: DetailMode):
    from . import profile
    return {"result": profile.set_mode(auth.current_owner(), payload.detail_mode)}


@app.get("/api/v1/home")
def personal_home():
    from . import home
    return {"result": home.build(auth.current_owner())}


@app.get("/api/v1/world-news")
def world_news():
    from .research import world_news as news
    return {"result": news.view(auth.current_owner())}


@app.post("/api/v1/world-news/refresh")
def refresh_world_news():
    from .research import world_news as news
    news.refresh()
    return {"result": news.view(auth.current_owner())}


@app.post("/api/v1/world-news/check")
def check_world_news():
    from .research import world_news as news
    return {"result": news.check(auth.current_owner())}


@app.get("/api/v1/portfolio")
def portfolio_read():
    from . import portfolio
    return {"result": portfolio.build(auth.current_owner())}


@app.post("/api/v1/portfolio/explain")
def explain_portfolio():
    from . import portfolio
    return {"result": portfolio.explain(auth.current_owner())}


@app.get("/api/v1/watchlist")
def get_watchlist():
    from . import watchlist
    return {"result": watchlist.summary(auth.current_owner())}


@app.post("/api/v1/watchlist")
def add_to_watchlist(payload: WatchlistCompany):
    from . import watchlist
    return {"result": watchlist.add(auth.current_owner(), str(payload.instrument_id))}


@app.delete("/api/v1/watchlist/{instrument_id}")
def remove_from_watchlist(instrument_id: UUID):
    from . import watchlist
    return {"result": watchlist.remove(auth.current_owner(), str(instrument_id))}


@app.get("/api/v1/workspace")
def workspace(instrument_id: UUID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"), include_financials: bool = True):
    result = service.state(auth.current_owner(), str(instrument_id), include_financials=include_financials)
    from .db import transaction, one
    with transaction() as conn:
        result["workspace_reset_at"] = one(conn, "SELECT reset_at FROM workspace_settings WHERE singleton")["reset_at"]
    return {"result": result}


@app.get("/api/v1/home-cards")
def home_cards():
    from .home_cards import quotes

    return {"result": quotes(auth.current_owner())}


@app.get("/api/v1/companies/{instrument_id}/home-card")
def home_card(instrument_id: UUID, figures: bool = True):
    from .home_cards import card

    return {"result": card(auth.current_owner(), str(instrument_id), figures=figures)}


@app.get("/api/v1/companies/{instrument_id}/workspace-financials")
def workspace_financials(instrument_id: UUID):
    return {"result": service.financial_workspace(auth.current_owner(), str(instrument_id))}


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
            auth.current_owner(),
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
        auth.current_owner(), days=days, cutoff=cutoff, instrument_id=instrument_id, review=review
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
    return {"result": answers.generate(auth.current_owner(), str(instrument_id), payload)}


@app.get("/api/v1/companies/{instrument_id}/questions")
def research_questions(instrument_id: UUID, before: UUID | None = None):
    return {"result": answers.history(auth.current_owner(), str(instrument_id), before)}


from .research import question_library


@app.put("/api/v1/companies/{instrument_id}/question-library")
def save_research_question(instrument_id: UUID, payload: question_library.SaveQuestion):
    return {"result": question_library.save(auth.current_owner(), str(instrument_id), payload)}


@app.get("/api/v1/research-answers/{answer_id}")
def research_answer(answer_id: UUID):
    return {"result": answers.get(auth.current_owner(), str(answer_id))}


@app.get("/api/v1/research-answers/{answer_id}/export")
def research_answer_export(answer_id: UUID):
    name, html = answers.download(auth.current_owner(), str(answer_id))
    return HTMLResponse(
        html, headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


from .valuation import ScenarioRequest, SaveScenario


@app.get("/api/v1/companies/{instrument_id}/valuation")
def valuation_context(instrument_id: UUID):
    from .valuation import context

    return {"result": context(auth.current_owner(), str(instrument_id))}


@app.post("/api/v1/companies/{instrument_id}/multiples/refresh")
def refresh_multiples(instrument_id: UUID):
    from .research.multiples import refresh

    return {"result": refresh(str(instrument_id))}


@app.get("/api/v1/companies/{instrument_id}/fmp")
def fmp_research(instrument_id: UUID):
    from .research.fmp import context
    return {"result": context(auth.current_owner(), str(instrument_id))}


@app.get("/api/v1/companies/{instrument_id}/sector-position")
def sector_position(instrument_id: UUID, peers: str | None = None):
    from .research.sector_position import context
    if peers is not None and len(peers) > 127:
        raise ValueError('Choose up to eight comparison companies.')
    return {"result": context(auth.current_owner(), str(instrument_id), None if peers is None else peers.split(',') if peers else [])}


@app.post("/api/v1/companies/{instrument_id}/fmp/refresh")
def fmp_refresh(instrument_id: UUID):
    from .research.fmp import refresh_company
    return {"result": refresh_company(auth.current_owner(), str(instrument_id))}


@app.post("/api/v1/companies/{instrument_id}/financial-forecasts/refresh")
def public_financial_forecast_refresh(instrument_id: UUID):
    from .research.analyst_targets import refresh
    from .research.fmp import context
    refresh(str(instrument_id), purpose='financials')
    return {"result": context(auth.current_owner(), str(instrument_id))}


class PeerSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(min_length=1, max_length=15, pattern=r"^[A-Z][A-Z0-9.-]*$")
    rationale: str = Field(min_length=8, max_length=600)


class PeerSelections(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selections: list[PeerSelection] = Field(max_length=8)


@app.put("/api/v1/companies/{instrument_id}/fmp/peers")
def fmp_peers(instrument_id: UUID, payload: PeerSelections):
    from .research.fmp import save_peers
    return {"result": save_peers(auth.current_owner(), str(instrument_id), [item.model_dump() for item in payload.selections])}


@app.post("/api/v1/valuation/preview")
def valuation_preview(payload: ScenarioRequest):
    from .valuation import preview

    return {"result": preview(auth.current_owner(), payload)}


@app.post("/api/v1/companies/{instrument_id}/analyst-targets/refresh")
def refresh_analyst_targets(instrument_id: UUID):
    from .research.analyst_targets import refresh

    return {"result": refresh(str(instrument_id))}


@app.post("/api/v1/valuation/save")
def valuation_save(payload: SaveScenario):
    from .valuation import save

    return {"result": save(auth.current_owner(), payload)}


@app.get("/api/v1/valuations/{scenario_id}")
def valuation_record(scenario_id: UUID):
    from .valuation import get

    return {"result": get(auth.current_owner(), str(scenario_id))}


@app.get("/api/v1/valuations/{scenario_id}/export")
def valuation_export(scenario_id: UUID):
    from .valuation import download

    name, html = download(auth.current_owner(), str(scenario_id))
    return HTMLResponse(
        html, headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


@app.post("/api/v1/idea")
def save(payload: SaveIdea):
    return {"result": service.save_idea(auth.current_owner(), payload)}


@app.post("/api/v1/research-actions")
def research(payload: ResearchAction):
    service.research_action(auth.current_owner(), payload)
    return {"result": {"saved": True}}


@app.post("/api/v1/evaluations/{evaluation_id}/review")
def review(evaluation_id: UUID, payload: ReviewAction):
    return {"result": service.review(auth.current_owner(), evaluation_id, payload.action)}


@app.post("/api/v1/demo/advance")
def advance(payload: Advance):
    return {
        "result": service.advance(
            auth.current_owner(), payload.expected_stage, str(payload.instrument_id)
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

    return {"result": review_schedule.history(auth.current_owner(), before=before)}


@app.post("/api/v1/review-schedule")
def configure_review_schedule(payload: ReviewScheduleSettings):
    from .monitoring import review_schedule

    return {"result": review_schedule.configure(auth.current_owner(), **payload.model_dump())}


@app.get("/api/v1/scheduled-reviews/{review_id}")
def saved_review(review_id: UUID, page: int = 0):
    from .monitoring import review_schedule

    return {"result": review_schedule.read(auth.current_owner(), review_id, page=page)}


@app.get("/api/v1/scheduled-reviews/{review_id}/export")
def saved_review_export(review_id: UUID):
    from .monitoring import review_schedule

    name, html = review_schedule.download(auth.current_owner(), review_id)
    return HTMLResponse(
        html, headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


@app.post("/api/v1/scheduled-reviews/{review_id}/seen")
def saved_review_seen(review_id: UUID):
    from .monitoring import review_schedule

    return {"result": review_schedule.mark_seen(auth.current_owner(), review_id)}


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

    return {"result": history(auth.current_owner(), str(instrument_id), before)}


@app.get("/api/v1/research-alerts/{alert_id}/previous-sample")
def alert_previous_sample(alert_id: UUID):
    from .monitoring.news_watch import previous_sample

    return {"result": previous_sample(auth.current_owner(), str(alert_id))}


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
    publish(auth.current_owner(), str(instrument_id), result["id"])
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
            auth.current_owner(),
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

    return {"result": review(auth.current_owner(), str(alert_id), payload.action)}


@app.post("/api/v1/move-alerts/{alert_id}/review")
def review_move_alert(alert_id: UUID, payload: ReviewAction):
    from .monitoring.move_alerts import review
    return {"result": review(auth.current_owner(), str(alert_id), payload.action)}


class AlertRating(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: Literal["useful", "not_useful"]


@app.get('/api/v1/daily-updates')
def daily_update_history():
    from .monitoring.daily_updates import history
    return {'result':history(auth.current_owner())}


@app.get('/api/v1/daily-updates/{digest_id}')
def daily_update_detail(digest_id:UUID,page:int=0):
    from .monitoring.daily_updates import read
    return {'result':read(auth.current_owner(),str(digest_id),page=page)}


@app.post("/api/v1/alerts/{kind}/{alert_id}/rating")
def rate_saved_alert(kind: str, alert_id: UUID, payload: AlertRating):
    from .monitoring.alert_feedback import rate
    return {"result": rate(auth.current_owner(),kind,str(alert_id),payload.value)}


class SectorReferenceSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str | None


@app.get("/api/v1/companies/{instrument_id}/price-references")
def price_references(instrument_id: UUID):
    from .db import transaction
    from .research.reference_prices import present
    with transaction(auth.current_owner(), consistent=True) as conn:
        return {"result": present(conn, auth.current_owner(), str(instrument_id))}


@app.post("/api/v1/companies/{instrument_id}/price-references")
def change_price_reference(instrument_id: UUID, payload: SectorReferenceSettings):
    from .research.reference_prices import set_sector
    return {"result": set_sector(auth.current_owner(), str(instrument_id), payload.symbol)}


class EventWatchSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: UUID | None


@app.post("/api/v1/companies/{instrument_id}/event-watch")
def configure_event_watch(instrument_id: UUID, payload: EventWatchSettings):
    from .monitoring.event_watch import configure

    return {
        "result": configure(
            auth.current_owner(),
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
            auth.current_owner(),
            str(instrument_id),
            str(payload.analysis_id),
            str(payload.version_id),
            purpose=payload.purpose,
        )
    }


@app.post("/api/v1/idea-alerts/{check_id}/review")
def review_idea_alert(check_id: UUID, payload: ReviewAction):
    from .research.idea_alerts import review

    return {"result": review(auth.current_owner(), str(check_id), payload.action)}


@app.get("/api/v1/idea-alerts/{check_id}/export")
def export_idea_alert(check_id: UUID):
    from .research.idea_alerts import download

    filename, content = download(auth.current_owner(), str(check_id))
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
    service.queue_current(auth.current_owner())
    return {"result": result}


@app.get('/api/v1/companies/{instrument_id}/disclosures')
def original_filings(instrument_id: UUID):
    from .research.sec.disclosures import present
    from .db import transaction
    with transaction() as conn:
        return {'result':present(conn,str(instrument_id))}


@app.get('/api/v1/companies/{instrument_id}/business')
def business_briefs(instrument_id: UUID, before: UUID | None=None):
    from .research.business import history
    return {'result':history(str(instrument_id),str(before) if before else None)}


@app.post('/api/v1/companies/{instrument_id}/business')
def explain_business(instrument_id: UUID):
    from .research.business import generate
    return {'result':generate(str(instrument_id),owner=auth.current_owner())}


@app.get('/api/v1/companies/{instrument_id}/business/{record_id}/export')
def export_business(instrument_id: UUID, record_id: UUID):
    from .research.business import download
    name,html=download(str(instrument_id),str(record_id))
    return HTMLResponse(html,headers={'Content-Disposition':f'attachment; filename="{name}"'})


@app.post('/api/v1/companies/{instrument_id}/disclosures/refresh')
def refresh_original_filings(instrument_id: UUID):
    from .research.sec.disclosures import refresh
    return {'result':refresh(str(instrument_id))}


@app.get('/api/v1/companies/{instrument_id}/disclosures/{document_id}')
def original_filing(instrument_id: UUID, document_id: UUID):
    from .research.sec.disclosures import document
    return {'result':document(str(instrument_id),str(document_id))}


class FilingWatchSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool


@app.post("/api/v1/companies/{instrument_id}/filing-watch")
def configure_filing_watch(instrument_id: UUID, payload: FilingWatchSettings):
    from .monitoring.filing_watch import configure

    return {"result": configure(auth.current_owner(), str(instrument_id), payload.enabled)}


@app.get("/api/v1/companies/{instrument_id}/filing-checks")
def filing_checks(instrument_id: UUID, before: UUID | None = None):
    from .monitoring.filing_watch import history

    return {"result": history(auth.current_owner(), str(instrument_id), before)}


@app.get("/api/v1/companies/{instrument_id}/price-history")
def price_history(instrument_id: UUID):
    from .research.price_history import present

    return {"result": present(str(instrument_id))}


@app.get("/api/v1/companies/{instrument_id}/financial-story")
def financial_story(instrument_id: UUID):
    from .research.sec.financial_story import present
    from .db import transaction

    with transaction(auth.current_owner(),consistent=True) as conn:
        return {"result": present(conn, str(instrument_id))}


@app.get('/api/v1/companies/{instrument_id}/financial-recovery')
def financial_recovery_preview(instrument_id: UUID, document_id: UUID | None = None):
    from .research.sec.financial_recovery import present
    from .db import transaction
    with transaction(auth.current_owner(),consistent=True) as conn:
        return {'result':present(conn,str(instrument_id),str(document_id) if document_id else None)}


class FinancialRecoveryRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    document_id: str
    plan_id: str


@app.post('/api/v1/companies/{instrument_id}/financial-recovery')
def financial_recovery_generate(instrument_id: UUID, payload: FinancialRecoveryRequest):
    from .research.sec.financial_recovery import generate
    return {'result':generate(auth.current_owner(),str(instrument_id),str(UUID(payload.document_id)),payload.plan_id)}


class FinancialRecoveryReview(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    accepted: list[str]
    expected_review: str | None


@app.post('/api/v1/companies/{instrument_id}/financial-recovery/{reading_id}/review')
def financial_recovery_review(instrument_id: UUID, reading_id: UUID, payload: FinancialRecoveryReview):
    from .research.sec.financial_recovery import review
    return {'result':review(auth.current_owner(),str(instrument_id),str(reading_id),payload.accepted,payload.expected_review)}


@app.post("/api/v1/companies/{instrument_id}/price-history/refresh")
def refresh_price_history(instrument_id: UUID):
    from .research.price_history import refresh

    return {"result": refresh(str(instrument_id))}


@app.post("/api/v1/market/{instrument_id}/refresh")
def refresh_market(instrument_id: UUID):
    from .research.market import refresh

    result = refresh(str(instrument_id))
    service.queue_current(auth.current_owner())
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
            auth.current_owner(),
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
            auth.current_owner(),
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
        auth.current_owner(),
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
            auth.current_owner(), payload.proposal_ids, definition=payload.definition
        )
    }


@app.post("/api/v1/proposals/generate")
def generate_proposals(payload: GenerateRequest):
    from .research.proposals import generate

    return {"result": generate(auth.current_owner(), payload)}


@app.post("/api/v1/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: UUID, payload: SaveIdea):
    from .research.proposals import decide

    return {"result": decide(auth.current_owner(), str(proposal_id), definition=payload)}


@app.post("/api/v1/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: UUID):
    from .research.proposals import decide

    return {"result": decide(auth.current_owner(), str(proposal_id))}


class TelegramDeliverySetting(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool


@app.get("/api/v1/telegram")
def telegram_status():
    from .monitoring import telegram
    return {"result": telegram.status(auth.current_owner())}


@app.post("/api/v1/telegram/connect")
def telegram_connect():
    from .monitoring import telegram
    return {"result": telegram.connect(auth.current_owner())}


@app.post("/api/v1/telegram/check")
def telegram_check():
    from .monitoring import telegram
    return {"result": telegram.check_connection(auth.current_owner())}


@app.post("/api/v1/telegram/delivery")
def telegram_delivery(payload: TelegramDeliverySetting):
    from .monitoring import telegram
    return {"result": telegram.configure(auth.current_owner(), payload.enabled)}


@app.post("/api/v1/telegram/disconnect")
def telegram_disconnect():
    from .monitoring import telegram
    return {"result": telegram.disconnect(auth.current_owner())}


@app.post("/api/v1/telegram/test")
def telegram_test():
    from .monitoring import telegram
    return {"result": telegram.test_message(auth.current_owner())}


dist = ROOT / "frontend" / "dist"
if os.environ.get("THESIS_TEST_OFFLINE") == "true" and DATA.is_relative_to("/private/tmp"):
    dist = Path(os.environ.get("THESIS_FRONTEND_DIST", str(dist)))
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    if (dist / "fonts").exists():
        app.mount("/fonts", StaticFiles(directory=dist / "fonts"), name="fonts")


@app.get("/")
@app.get("/terms")
@app.get("/privacy")
def index():
    return FileResponse(dist / "index.html")


class ResearchLoadSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    initial: bool = False
    analyze: bool = False
    lookback_days: Literal[1, 7, 30] = 7
    reread: bool = False
    split_failed: bool = False


@app.get("/api/v1/companies/{instrument_id}/loading")
def research_loading(instrument_id: UUID):
    from .research.loading import latest
    return {"result": latest(auth.current_owner(), str(instrument_id))}


@app.post("/api/v1/companies/{instrument_id}/loading")
def start_research_loading(instrument_id: UUID, payload: ResearchLoadSettings):
    from .research.loading import start
    return {"result": start(auth.current_owner(), str(instrument_id), **payload.model_dump())}
