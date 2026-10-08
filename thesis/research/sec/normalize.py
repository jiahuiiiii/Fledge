"""Normalize first-party SEC facts without pretending fiscal periods are calendar quarters.

Only whole-entity US-GAAP USD revenue and operating income in one exact accession
are used. No mixing current/comparative facts from different filing vintages.
"""

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, localcontext
import json
import re

REVENUE = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
)
CONCEPTS = REVENUE + ("OperatingIncomeLoss",)
METHOD = "sec-fiscal-ratios-1"


def filing_rows(submissions, now):
    data = submissions.get("filings", {}).get("recent", {})
    keys = (
        "accessionNumber",
        "filingDate",
        "reportDate",
        "form",
        "primaryDocument",
        "acceptanceDateTime",
    )
    lengths = {len(data.get(k, [])) for k in keys}
    if len(lengths) != 1:
        raise ValueError("SEC filing columns are incomplete")
    result = []
    for values in zip(*(data[k] for k in keys)):
        r = dict(zip(keys, values))
        if r["form"] not in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
            continue
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", r["accessionNumber"]):
            raise ValueError("Invalid filing accession")
        # SEC API supplies an ISO acceptance timestamp. Do not infer a timezone.
        accepted = datetime.fromisoformat(
            r["acceptanceDateTime"].replace("Z", "+00:00")
        )
        if accepted.tzinfo is None:
            raise ValueError("SEC acceptance timestamp needs a timezone")
        r["accepted_at"] = accepted
        r["end"] = date.fromisoformat(r["reportDate"])
        r["filed"] = date.fromisoformat(r["filingDate"])
        if r["end"] > r["filed"] or accepted > now:
            continue
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", r["primaryDocument"]):
            raise ValueError("Invalid filing document path")
        result.append(r)
    if not result:
        raise ValueError("No supported recent financial filing is available")
    # New annual/quarter reports win; amendments of older periods do not move the
    # active period backwards. Amendments of the latest period are visible gaps if
    # they omit financial tables; never silently substitute an older accession.
    return sorted(
        result, key=lambda r: (r["end"], r["accepted_at"], r["accessionNumber"])
    )


def normalize(companyfacts, submissions, cik, now):
    if now.tzinfo is None:
        raise ValueError("Retrieval time needs a timezone")
    if str(companyfacts.get("cik")).lstrip("0") != str(cik) or str(
        submissions.get("cik")
    ).lstrip("0") != str(cik):
        raise ValueError("SEC evidence belongs to another company")
    filing = filing_rows(submissions, now)[-1]
    period_type = "annual" if filing["form"].startswith("10-K") else "quarter"
    accession = filing["accessionNumber"]
    facts = []
    for concept in CONCEPTS:
        for r in (
            companyfacts.get("facts", {})
            .get("us-gaap", {})
            .get(concept, {})
            .get("units", {})
            .get("USD", [])
        ):
            if (
                r.get("accn") != accession
                or r.get("form") != filing["form"]
                or r.get("filed") != filing["filingDate"]
            ):
                continue
            if not r.get("start") or not r.get("end"):
                continue
            start, end = date.fromisoformat(r["start"]), date.fromisoformat(r["end"])
            value = Decimal(str(r["val"]))
            if not value.is_finite() or end < start or end > filing["filed"]:
                raise ValueError("Invalid financial fact")
            if abs(value.adjusted()) > 100 or len(value.as_tuple().digits) > 100:
                raise ValueError("Financial fact exceeds supported decimal precision")
            numeric_text = format(value, "f")
            if "." in numeric_text:
                numeric_text = numeric_text.rstrip("0").rstrip(".")
            facts.append(
                dict(
                    concept=concept,
                    namespace="us-gaap",
                    unit="USD",
                    value=numeric_text,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    accession=accession,
                    filed=r["filed"],
                    form=r["form"],
                    fy=r.get("fy"),
                    fp=r.get("fp"),
                    frame=r.get("frame"),
                )
            )
    minimum, maximum = (350, 380) if period_type == "annual" else (70, 110)

    def duration(f):
        return (date.fromisoformat(f["end"]) - date.fromisoformat(f["start"])).days + 1

    def select(concepts, end=None, prior_to=None):
        choices = [
            f
            for f in facts
            if f["concept"] in concepts and minimum <= duration(f) <= maximum
        ]
        if end is not None:
            choices = [f for f in choices if f["end"] == end.isoformat()]
        if prior_to is not None:
            choices = [
                f
                for f in choices
                if 357
                <= (
                    date.fromisoformat(prior_to["end"]) - date.fromisoformat(f["end"])
                ).days
                <= 373
                and abs(duration(f) - duration(prior_to)) <= 7
            ]
        scopes = {(f["start"], f["end"], Decimal(f["value"])) for f in choices}
        if len(scopes) > 1:
            return None, "Conflicting values or fiscal periods in this filing"
        if not choices:
            return None, "No compatible USD fact in the selected filing"
        return (
            sorted(
                choices,
                key=lambda f: (
                    concepts.index(f["concept"]),
                    json.dumps(f, sort_keys=True),
                ),
            )[0],
            None,
        )

    revenue, rev_error = select(REVENUE, end=filing["end"])
    income, inc_error = select(("OperatingIncomeLoss",), end=filing["end"])
    prior, prior_error = (
        select(REVENUE, prior_to=revenue) if revenue else (None, rev_error)
    )
    calculations = []
    for metric, inputs, formula, error in (
        (
            "revenue_growth",
            [revenue, prior],
            "(revenue / prior_revenue - 1) × 100",
            rev_error or prior_error,
        ),
        (
            "operating_margin",
            [income, revenue],
            "operating_income / revenue × 100",
            rev_error or inc_error,
        ),
    ):
        value = None
        if not error:
            if metric == "operating_margin" and (income["start"], income["end"]) != (
                revenue["start"],
                revenue["end"],
            ):
                error = "Revenue and operating income cover different periods"
            elif Decimal(inputs[1]["value"]) <= 0:
                error = "The denominator must be positive; this ratio is undefined here"
            else:
                with localcontext() as ctx:
                    ctx.prec = 28
                    ratio = Decimal(inputs[0]["value"]) / Decimal(inputs[1]["value"])
                    value = (
                        (ratio - 1) * 100 if metric == "revenue_growth" else ratio * 100
                    )
                if not Decimal("-100") <= value <= Decimal("1000"):
                    error = "Result is outside the supported monitoring range"
                    value = None
        calculations.append(
            dict(
                metric=metric,
                value=str(value) if value is not None else None,
                formula=formula,
                inputs=[f for f in inputs if f],
                reason=error,
                method=METHOD,
                arithmetic="Decimal, 28 significant digits; no display rounding before evaluation",
            )
        )
    return dict(
        cik=cik,
        name=submissions.get("name") or companyfacts.get("entityName"),
        accession=accession,
        form=filing["form"],
        published_at=filing["accepted_at"],
        filed_on=filing["filed"],
        period_type=period_type,
        period=f"{'Year' if period_type=='annual' else 'Quarter'} ended {filing['end']}",
        period_end=filing["end"],
        period_start=date.fromisoformat(revenue["start"]) if revenue else None,
        filing_url=f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-','')}/{filing['primaryDocument']}",
        facts=facts,
        calculations=calculations,
        limitations=[
            "US-GAAP whole-entity USD facts only; custom taxonomy and segment facts are not used.",
            "Annual and quarterly results are distinct. No annual-minus-year-to-date quarter is inferred.",
            "Comparisons use the same filing accession; later comparative revisions do not rewrite saved history.",
            "Figures are structured filing data, not audited by this application. Consensus, price data and news coverage are not supplied by this source.",
        ],
    )
