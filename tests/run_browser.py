"""Run browser.cjs against a new isolated fictional database; no user history changes."""

import os
import sys
import tempfile
import time
import subprocess
import urllib.request
from pathlib import Path

journeys = {
    "--business",
    "--watch-continuity",
    "--research-design",
    "--source-filters",
    "--sentiment-limits",
    "--age",
    "--answer-evidence",
    "--catalogue",
    "--conversation",
    "--digest",
    "--scheduled-review",
    "--event",
    "--event-occurrence",
    "--recurring-events",
    "--report-expectations",
    "--event-watch",
    "--expectations",
    "--filing-watch",
    "--idea",
    "--idea-alert",
    "--inbox",
    "--market",
    "--original-sources",
    "--performance",
    "--prices",
    "--proposal",
    "--questions",
    "--reporting-updates",
    "--roles",
    "--sec",
    "--sentiment",
    "--sentiment-inputs",
    "--sentiment-history",
    "--social-platforms",
    "--themes",
    "--valuation",
    "--watch-history",
}
if len(sys.argv) > 2 or any(arg not in journeys for arg in sys.argv[1:]):
    raise SystemExit(
        "Choose one supported browser journey: " + ", ".join(sorted(journeys))
    )

root = Path(__file__).resolve().parents[1]
env = dict(
    os.environ,
    THESIS_DATA_DIR=tempfile.mkdtemp(prefix="thesis-browser-", dir="/private/tmp"),
    THESIS_TEST_URL="http://127.0.0.1:8843",
    THESIS_TEST_OFFLINE="true",
    PYTHONPATH=str(root / "tests/offline_runtime") + os.pathsep + str(root),
)
if "--research-design" in sys.argv:
    env["THESIS_DESIGN_SYMBOL"] = "MSFT"
if "--source-filters" in sys.argv:
    env["THESIS_FILTERS_SYMBOL"] = "MSFT"
server = subprocess.Popen(
    [sys.executable, "run.py", "--port", "8843"], cwd=root, env=env
)
try:
    for _ in range(60):
        if server.poll() is not None:
            raise RuntimeError("Browser test server exited")
        try:
            urllib.request.urlopen(
                env["THESIS_TEST_URL"] + "/api/v1/session", timeout=1
            ).close()
            break
        except OSError:
            time.sleep(0.2)
    else:
        raise RuntimeError("Browser test server did not start")
    if "--business" in sys.argv:
        subprocess.run([sys.executable, "tests/seed_business_browser.py"], cwd=root, env=env, check=True)
    elif "--watch-continuity" in sys.argv:
        subprocess.run([sys.executable, "tests/seed_retained_watch_browser.py"], cwd=root, env=env, check=True)
    elif "--sentiment-limits" in sys.argv:
        subprocess.run([sys.executable, "tests/seed_sentiment_limits_browser.py"], cwd=root, env=env, check=True)
    elif "--recurring-events" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_recurring_events_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--event-occurrence" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_event_occurrence_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--scheduled-review" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_scheduled_review_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--answer-evidence" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_answer_evidence_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif any(flag in sys.argv for flag in ("--sentiment-inputs", "--research-design", "--source-filters")):
        subprocess.run(
            [sys.executable, "tests/seed_sentiment_inputs_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--themes" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_themes_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--conversation" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_conversation_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--event-watch" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_event_watch_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--filing-watch" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_filing_watch_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--social-platforms" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_social_platforms_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--expectations" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_expectation_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--inbox" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_inbox_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--reporting-updates" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_reporting_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--original-sources" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_sentiment_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--catalogue" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_catalogue_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--sentiment-history" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_sentiment_history_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--watch-history" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_watch_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--questions" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_question_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--prices" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_price_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--valuation" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_valuation_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--performance" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_performance_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--digest" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_digest_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--idea-alert" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_idea_alert_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--sentiment" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_sentiment_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--proposal" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_proposal_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--idea" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_idea_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    elif "--market" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_market_browser.py"],
            cwd=root,
            env=env,
            check=True,
        )
    if "--sec" in sys.argv:
        subprocess.run(
            [sys.executable, "tests/seed_sec_browser.py"], cwd=root, env=env, check=True
        )
    if "--research-design" in sys.argv:
        subprocess.run([sys.executable, "tests/seed_price_browser.py"], cwd=root, env=env, check=True)
    result = subprocess.run(
        [
            os.environ.get("THESIS_NODE", "node"),
            "tests/browser_business.cjs" if "--business" in sys.argv else "tests/browser_research_design.cjs" if "--research-design" in sys.argv else "tests/browser_source_filters.cjs" if "--source-filters" in sys.argv else "tests/browser_retained_watch.cjs" if "--watch-continuity" in sys.argv else "tests/browser_sentiment_limits.cjs" if "--sentiment-limits" in sys.argv else "tests/browser_report_expectations.cjs" if "--report-expectations" in sys.argv else (
                (
                    "tests/browser_recurring_events.cjs"
                    if "--recurring-events" in sys.argv
                    else "tests/browser_event_occurrence.cjs"
                )
                if (
                    "--event-occurrence" in sys.argv or "--recurring-events" in sys.argv
                )
                else (
                    "tests/browser_scheduled_review.cjs"
                    if (
                        "--scheduled-review" in sys.argv
                        or "--event-occurrence" in sys.argv
                    )
                    else (
                        "tests/browser_answer_evidence.cjs"
                        if "--answer-evidence" in sys.argv
                        or "--scheduled-review" in sys.argv
                        else (
                            "tests/browser_sentiment_inputs.cjs"
                            if "--sentiment-inputs" in sys.argv
                            else (
                                "tests/browser_themes.cjs"
                                if "--themes" in sys.argv
                                else (
                                    "tests/browser_conversation.cjs"
                                    if "--conversation" in sys.argv
                                    else (
                                        "tests/browser_event_watch.cjs"
                                        if "--event-watch" in sys.argv
                                        else (
                                            "tests/browser_filing_watch.cjs"
                                            if "--filing-watch" in sys.argv
                                            else (
                                                "tests/browser_social_platforms.cjs"
                                                if "--social-platforms" in sys.argv
                                                else (
                                                    "tests/browser_roles.cjs"
                                                    if "--roles" in sys.argv
                                                    else (
                                                        "tests/browser_expectations.cjs"
                                                        if "--expectations" in sys.argv
                                                        else (
                                                            "tests/browser_inbox.cjs"
                                                            if "--inbox" in sys.argv
                                                            else (
                                                                "tests/browser_reporting.cjs"
                                                                if "--reporting-updates"
                                                                in sys.argv
                                                                else (
                                                                    "tests/browser_source_reading.cjs"
                                                                    if "--original-sources"
                                                                    in sys.argv
                                                                    else (
                                                                        "tests/browser_catalogue.cjs"
                                                                        if "--catalogue"
                                                                        in sys.argv
                                                                        else (
                                                                            "tests/browser_sentiment_history.cjs"
                                                                            if "--sentiment-history"
                                                                            in sys.argv
                                                                            else (
                                                                                "tests/browser_watch.cjs"
                                                                                if "--watch-history"
                                                                                in sys.argv
                                                                                else (
                                                                                    "tests/browser_questions.cjs"
                                                                                    if "--questions"
                                                                                    in sys.argv
                                                                                    else (
                                                                                        "tests/browser_prices.cjs"
                                                                                        if "--prices"
                                                                                        in sys.argv
                                                                                        else (
                                                                                            "tests/browser_valuation.cjs"
                                                                                            if "--valuation"
                                                                                            in sys.argv
                                                                                            else (
                                                                                                "tests/browser_performance.cjs"
                                                                                                if "--performance"
                                                                                                in sys.argv
                                                                                                else (
                                                                                                    "tests/browser_digest.cjs"
                                                                                                    if "--digest"
                                                                                                    in sys.argv
                                                                                                    else (
                                                                                                        "tests/browser_idea_alert.cjs"
                                                                                                        if "--idea-alert"
                                                                                                        in sys.argv
                                                                                                        else (
                                                                                                            "tests/browser_sentiment.cjs"
                                                                                                            if "--sentiment"
                                                                                                            in sys.argv
                                                                                                            else (
                                                                                                                "tests/browser_proposal.cjs"
                                                                                                                if "--proposal"
                                                                                                                in sys.argv
                                                                                                                else (
                                                                                                                    "tests/browser_event.cjs"
                                                                                                                    if "--event"
                                                                                                                    in sys.argv
                                                                                                                    else (
                                                                                                                        "tests/browser_idea.cjs"
                                                                                                                        if "--idea"
                                                                                                                        in sys.argv
                                                                                                                        else (
                                                                                                                            "tests/browser_market.cjs"
                                                                                                                            if "--market"
                                                                                                                            in sys.argv
                                                                                                                            else (
                                                                                                                                "tests/browser_sec.cjs"
                                                                                                                                if "--sec"
                                                                                                                                in sys.argv
                                                                                                                                else (
                                                                                                                                    "tests/browser_age.cjs"
                                                                                                                                    if "--age"
                                                                                                                                    in sys.argv
                                                                                                                                    else "tests/browser.cjs"
                                                                                                                                )
                                                                                                                            )
                                                                                                                        )
                                                                                                                    )
                                                                                                                )
                                                                                                            )
                                                                                                        )
                                                                                                    )
                                                                                                )
                                                                                            )
                                                                                        )
                                                                                    )
                                                                                )
                                                                            )
                                                                        )
                                                                    )
                                                                )
                                                            )
                                                        )
                                                    )
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            ),
        ],
        cwd=root,
        env=env,
    )
    raise SystemExit(result.returncode)
finally:
    server.terminate()
    server.wait(timeout=10)
    subprocess.run(
        [sys.executable, "run.py", "--stop-db"], cwd=root, env=env, check=True
    )
