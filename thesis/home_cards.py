"""Light reads for the home company cards.

A card shows a quote, a news-tone line and two trailing filing figures, not
the whole research workspace. Quotes for every company come in one fast read
so cards can appear at once; tone and figures come per company, so slow
filing figures never hold back the prices. Readings pass through the same
presenters as the workspace, so withheld sources stay withheld.
"""
from . import service
from .db import rows, transaction

FIGURES = ("revenue", "operating_margin")


def quotes(owner):
    from .research.market import workspace as market_workspace

    with transaction(owner, consistent=True) as conn:
        return [
            dict(
                id=str(company["id"]),
                market=dict(quote=market_workspace(conn, str(company["id"]))["quote"]),
            )
            for company in service.catalogue(conn, owner)
        ]


def news_tone(reading):
    """Only what the card's news-tone line reads from a saved reading."""
    if not reading:
        return None
    if reading.get("withheld"):
        return dict(withheld=True)
    summary = reading.get("summary") or {}
    return dict(
        withheld=False,
        id=reading.get("id"),
        created_at=reading.get("created_at"),
        stale=reading.get("stale"),
        summary_policy=reading.get("summary_policy"),
        summary=dict(
            news=summary.get("news"),
            social_platforms=summary.get("social_platforms") or {},
        ),
    )


def trailing_figures(depth):
    """The card's two trailing figures, with the depth status kept honest."""
    if not depth or depth.get("status") != "available":
        return depth and dict(status=depth.get("status"), reason=depth.get("reason"))
    return dict(
        status="available",
        trailing=[row for row in depth.get("trailing") or [] if row.get("key") in FIGURES],
    )


def card(owner, instrument_id, *, figures=True):
    from .research import sentiment
    from .research.sec import financial_depth

    with transaction(owner, consistent=True) as conn:
        mode = service.stage_info(conn, instrument_id)["mode"]
        depth = (
            financial_depth.present(conn, instrument_id)
            if figures and mode == "sec"
            else None
        )
        return dict(
            id=str(instrument_id),
            sentiment=news_tone(sentiment.latest(conn, instrument_id)),
            financial_depth=trailing_figures(depth),
            figures=bool(figures and mode == "sec"),
        )


def warm_figures(stop=None, pause=0.5):
    """Parse every SEC company's filings once, so the cache is warm before
    anyone asks. Without an account nothing is saved; each account saves its
    own figures on its first read. Reads saved data only; returns how many."""
    from .research.sec import financial_depth

    with transaction(consistent=True) as conn:
        ids = [
            str(row["instrument_id"])
            for row in rows(conn, "SELECT instrument_id FROM instrument_state WHERE mode='sec' ORDER BY instrument_id")
        ]
    done = 0
    for instrument_id in ids:
        if stop is not None and (stop.is_set() or (done and stop.wait(pause))):
            break
        with transaction(consistent=True) as conn:
            financial_depth.present(conn, instrument_id)
        done += 1
    return done
