"""Adapted from Deus article normalization and aggregator. See PROVENANCE.md.

This boundary accepts recorded articles only. Failures are explicit rather than
Deus's historical empty-list fallback. Content versions are not URL-deduped away.
"""

from hashlib import sha256
from .deus_models import NewsArticle


def normalize_article(record):
    article = NewsArticle(**record)
    # Length separators avoid ambiguous headline/body concatenation in the original.
    article.content_hash = sha256(
        (article.headline + "\0" + article.summary).encode()
    ).hexdigest()
    if article.published_at.tzinfo is None or article.fetched_at.tzinfo is None:
        raise ValueError("Source timestamps require a timezone")
    if article.fetched_at < article.published_at:
        raise ValueError("Evidence cannot be available before publication")
    return article


def evidence_from_articles(rows):
    # Adapted from Deus pipeline/grounded_answer.py::_evidence_from_articles.
    return [
        dict(
            id=str(row["id"]),
            title=row["headline"].strip(),
            source=row["source_name"],
            published_at=row["published_at"].isoformat(),
            available_at=row["available_at"].isoformat(),
            body=row["body"],
            kind=(
                "recorded"
                if row.get("entitlement", "fictional") == "fictional"
                else (
                    "news"
                    if row.get("entitlement") in ("finnhub-pitch", "public-news")
                    else "sec-calculation"
                )
            ),
            url=row.get("url"),
            supersedes_id=(
                str(row["supersedes_id"]) if row.get("supersedes_id") else None
            ),
            content_hash=row["content_hash"],
        )
        for row in rows
        if row.get("headline", "").strip()
    ]


def validate_claim(claim, document):
    # Quote presence is only traceability. Fixture interpretations are authored;
    # no model is being represented as having verified entailment.
    if claim["instrument_id"] != document["instrument_id"]:
        raise ValueError("Claim belongs to another company")
    if not claim["quote"] or claim["quote"] not in document["body"]:
        raise ValueError("Claim quote is absent from the original source")
    if claim["available_at"] < document["available_at"]:
        raise ValueError("Claim predates its source")
