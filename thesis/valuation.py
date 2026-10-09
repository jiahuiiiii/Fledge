"""Explicit, private valuation assumptions; deterministic equity-multiple scenarios."""

from datetime import date, datetime, timezone
from calendar import monthrange
from decimal import Decimal, localcontext
from hashlib import sha256
from html import escape
import json
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from psycopg.types.json import Jsonb
from .db import transaction, one, rows
from .service import Missing, Conflict
from .research.sec.performance import decimal_text
from .research.sec.service import collection_lock
from .research import multiples, analyst_targets
from .price_reference import PriceReference, extend as extend_prices

METHOD = "equity-multiples-1"


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=60)
    growth: Decimal = Field(
        ge=-100, le=200, max_digits=12, decimal_places=6, allow_inf_nan=False
    )
    margin: Decimal | None = Field(
        default=None,
        ge=-100,
        le=100,
        max_digits=12,
        decimal_places=6,
        allow_inf_nan=False,
    )
    multiple: Decimal = Field(
        gt=0, le=200, max_digits=12, decimal_places=6, allow_inf_nan=False
    )
    rationale: str = Field(min_length=3, max_length=1200)
    reference_id: UUID | None = None

    @field_validator("name", "rationale")
    @classmethod
    def text(cls, value, info):
        if len(value.strip()) < (3 if info.field_name == "rationale" else 1):
            raise ValueError("Explain the assumption.")
        return value.strip()


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instrument_id: UUID
    performance_id: UUID
    title: str = Field(min_length=1, max_length=120)
    method: Literal["earnings", "sales"]
    years: int = Field(ge=1, le=5, strict=True)
    cases: list[Case] = Field(min_length=1, max_length=3)
    price_reference: PriceReference | None = None
    growth_step: Decimal = Field(
        gt=0, le=50, max_digits=8, decimal_places=4, allow_inf_nan=False
    )
    margin_step: Decimal = Field(
        gt=0, le=50, max_digits=8, decimal_places=4, allow_inf_nan=False
    )

    @model_validator(mode="after")
    def complete(self):
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Name the comparison.")
        if len({c.name.casefold() for c in self.cases}) != len(self.cases):
            raise ValueError("Give each case a distinct name.")
        if self.method == "earnings" and any(c.margin is None for c in self.cases):
            raise ValueError("Choose a net margin for each earnings case.")
        if self.method == "sales" and any(c.margin is not None for c in self.cases):
            raise ValueError("Sales-multiple cases do not use a profit margin.")
        return self


class SaveScenario(ScenarioRequest):
    request_id: UUID


def assumptions(request):
    data = request.model_dump(mode="json", exclude={"request_id"})
    if request.price_reference is None:
        data.pop("price_reference", None)
    return data


def outcome(revenue, growth, margin, multiple, years, method):
    with localcontext() as ctx:
        ctx.prec = 28
        projected = revenue * (1 + growth / 100) ** years
        profit = projected * margin / 100 if margin is not None else None
        usable = projected > 0 and (method == "sales" or profit > 0)
        value = (
            (profit if method == "earnings" else projected) * multiple
            if usable
            else None
        )
        return dict(
            revenue=decimal_text(projected),
            net_income=decimal_text(profit) if profit is not None else None,
            equity_value=decimal_text(value) if value is not None else None,
            reason=(
                None
                if usable
                else (
                    "Positive projected earnings are required for this P/E scenario."
                    if method == "earnings"
                    else "Positive projected revenue is required for this P/S scenario."
                )
            ),
        )


def calculate(packet, request):
    revenue = Decimal(packet["base"]["value"])
    end = date.fromisoformat(packet["report"]["period_end"])
    year = end.year + request.years
    target = date(year, end.month, min(end.day, monthrange(year, end.month)[1]))
    cases = []
    for c in request.cases:
        result = outcome(
            revenue, c.growth, c.margin, c.multiple, request.years, request.method
        )
        growths = sorted(
            {
                max(
                    Decimal(-100), min(Decimal(200), c.growth + x * request.growth_step)
                )
                for x in (-1, 0, 1)
            }
        )
        if request.method == "earnings":
            columns = sorted(
                {
                    max(
                        Decimal(-100),
                        min(Decimal(100), c.margin + x * request.margin_step),
                    )
                    for x in (-1, 0, 1)
                }
            )
        else:
            columns = sorted(
                {
                    min(Decimal(200), c.multiple * x)
                    for x in (Decimal(".75"), Decimal(1), Decimal("1.25"))
                }
            )
        grid = []
        for growth in growths:
            grid.append(
                dict(
                    growth=decimal_text(growth),
                    cells=[
                        outcome(
                            revenue,
                            growth,
                            column if request.method == "earnings" else None,
                            c.multiple if request.method == "earnings" else column,
                            request.years,
                            request.method,
                        )
                        for column in columns
                    ],
                )
            )
        cases.append(
            dict(
                name=c.name,
                **result,
                sensitivity=dict(
                    column=(
                        "net_margin_percent"
                        if request.method == "earnings"
                        else "price_sales_multiple"
                    ),
                    columns=[decimal_text(v) for v in columns],
                    rows=grid,
                )
            )
        )
    result = dict(
        method=METHOD,
        target_period_end=target.isoformat(),
        currency="USD",
        unit="total_equity_value",
        cases=cases,
        formulas=[
            "Projected annual revenue = reported annual revenue × (1 + annual growth / 100)^years",
            *(
                [
                    "Projected net income = projected annual revenue × assumed net margin / 100"
                ]
                if request.method == "earnings"
                else []
            ),
            (
                "Equity value = projected net income × P/E"
                if request.method == "earnings"
                else "Equity value = projected annual revenue × P/S"
            ),
        ],
        limitations=[
            "Scenario values apply at the selected horizon after the base reporting year and are undiscounted. The date is a calendar anniversary, not an inferred future fiscal-calendar date.",
            "These are user assumptions, not forecasts, consensus, fair-value estimates or expected returns. Dividends are excluded.",
            "Values cover total company equity. No share-count, share-class, dilution or per-share price conversion is made.",
            "P/E uses the assumed net income attributable to common equity after interest and tax. Sales multiples remain sensitive to profitability and financing differences.",
            "Comparisons with other companies do not establish suitable peers. Finnhub TTM reference multiples and this annual-base projection use different periods.",
        ],
    )
    return extend_prices(result, request.price_reference) if request.price_reference else result


def packet_for(conn, request):
    if not one(
        conn,
        "SELECT id FROM sources WHERE id='sec-companyfacts' AND entitlement='sec-public'",
    ):
        raise ValueError("Structured filing source access is unavailable.")
    record = one(
        conn,
        "SELECT p.*,i.symbol,i.name,c.snapshot_id current_id,c.checked_at FROM performance_snapshots p JOIN instruments i ON i.id=p.instrument_id JOIN performance_current c ON c.instrument_id=p.instrument_id WHERE p.id=%s AND p.instrument_id=%s",
        (request.performance_id, request.instrument_id),
    )
    if not record:
        raise Missing("Financial snapshot not found for this company.")
    if record["id"] != record["current_id"]:
        raise Conflict(
            "Financial data changed. Review the latest annual base before calculating or saving."
        )
    report = record["data"]["reports"].get("annual")
    if not report:
        raise ValueError(
            "A compatible annual filing is required; quarterly figures are not annualised."
        )
    base = next((m for m in report["metrics"] if m["key"] == "revenue"), None)
    if not base or base["value"] is None or Decimal(base["value"]) <= 0:
        raise ValueError("Positive compatible annual revenue is required.")
    if request.price_reference:
        as_of = request.price_reference.valuation_date
        if as_of > datetime.now(timezone.utc).date():
            raise ValueError("The valuation date cannot be in the future.")
        if as_of < date.fromisoformat(report["filed_on"]):
            raise ValueError("The valuation date must be on or after the base filing date.")
    references = []
    for case in request.cases:
        if not case.reference_id:
            continue
        if not multiples.allowed(conn):
            raise ValueError("Reference multiple source access is unavailable.")
        ref = one(
            conn,
            "SELECT id,instrument_id,symbol,metrics,retrieved_at FROM multiple_references WHERE id=%s",
            (case.reference_id,),
        )
        if not ref:
            raise Missing("Reference multiple not found.")
        value = ref["metrics"][request.method]["value"]
        if value is None or Decimal(value) != case.multiple:
            raise ValueError(
                "The selected reference differs from this multiple. Use a personal assumption or select the reference again."
            )
        references.append(json.loads(json.dumps(ref, default=str)))
    return dict(
        performance_id=str(record["id"]),
        payload_id=str(record["payload_id"]),
        symbol=record["symbol"],
        name=record["name"],
        source_checked_at=record["checked_at"].isoformat(),
        report={
            k: report[k]
            for k in (
                "accession",
                "form",
                "period_end",
                "published_at",
                "filed_on",
                "filing_url",
            )
        },
        base=base,
        references=references,
    )


def preview(owner, request):
    with transaction(owner, consistent=True) as conn:
        packet = packet_for(conn, request)
        return dict(
            assumptions=assumptions(request),
            packet=packet,
            result=calculate(packet, request),
            saved=False,
            withheld=False,
        )


def permitted(conn, record):
    return bool(
        one(
            conn,
            "SELECT id FROM sources WHERE id='sec-companyfacts' AND entitlement='sec-public'",
        )
    ) and (not record["packet"]["references"] or multiples.allowed(conn))


def present(conn, record):
    visible = permitted(conn, record)
    current = one(
        conn,
        "SELECT snapshot_id FROM performance_current WHERE instrument_id=%s",
        (record["instrument_id"],),
    )
    return dict(
        id=record["id"],
        created_at=record["created_at"],
        instrument_id=record["instrument_id"],
        assumptions=record["assumptions"],
        packet=record["packet"] if visible else None,
        result=record["result"] if visible else None,
        saved=True,
        withheld=not visible,
        newer_financials_available=bool(
            current and current["snapshot_id"] != record["performance_id"]
        ),
    )


def save(owner, request):
    data = assumptions(request)
    digest = sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    with transaction(owner) as conn:
        collection_lock(conn)
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
            ("valuation:" + str(owner) + ":" + str(request.request_id),),
        )
        previous = one(
            conn,
            "SELECT * FROM valuation_scenarios WHERE owner_id=%s AND request_id=%s",
            (owner, request.request_id),
        )
        if previous:
            if previous["request_hash"] != digest:
                raise Conflict(
                    "This save identity already belongs to different assumptions."
                )
            return present(conn, previous)
        packet = packet_for(conn, request)
        result = calculate(packet, request)
        record = one(
            conn,
            "INSERT INTO valuation_scenarios(id,owner_id,instrument_id,performance_id,request_id,request_hash,assumptions,packet,result) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",
            (
                uuid4(),
                owner,
                request.instrument_id,
                request.performance_id,
                request.request_id,
                digest,
                Jsonb(data),
                Jsonb(packet),
                Jsonb(result),
            ),
        )
        return present(conn, record)


def get(owner, scenario_id):
    with transaction(owner, consistent=True) as conn:
        record = one(
            conn,
            "SELECT * FROM valuation_scenarios WHERE owner_id=%s AND id=%s",
            (owner, scenario_id),
        )
        if not record:
            raise Missing("Saved scenario not found.")
        return present(conn, record)


def context(owner, iid):
    with transaction(owner, consistent=True) as conn:
        if not one(
            conn,
            "SELECT instrument_id FROM sec_companies WHERE instrument_id=%s",
            (iid,),
        ):
            raise ValueError(
                "Choose a supported SEC operating-company workspace for valuation."
            )
        return dict(
            references=multiples.catalogue(conn),
            analyst_targets=analyst_targets.current(conn, iid),
            saved=rows(
                conn,
                "SELECT id,created_at,assumptions->>'title' title,assumptions->>'method' method FROM valuation_scenarios WHERE owner_id=%s AND instrument_id=%s ORDER BY created_at DESC,id DESC",
                (owner, iid),
            ),
        )


def download(owner, scenario_id):
    item = get(owner, scenario_id)
    esc = lambda x: escape(str(x), quote=True)
    parts = [
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'\"><title>Private valuation scenario</title><style>body{font:15px/1.6 system-ui;max-width:960px;margin:40px auto;padding:20px;color:#18262b}table{border-collapse:collapse;width:100%}td,th{padding:9px;border:1px solid #b9c4c8;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere}h2{margin-top:32px}</style>"
    ]
    a = item["assumptions"]
    parts += [
        "<h1>" + esc(a["title"]) + "</h1>",
        "<p>Private research assumptions. Saved "
        + esc(item["created_at"])
        + ". Downloaded "
        + esc(datetime.now(timezone.utc).isoformat())
        + ".</p>",
        "<h2>Your assumptions</h2><pre>" + esc(json.dumps(a, indent=2)) + "</pre>",
    ]
    if item["withheld"]:
        parts.append(
            "<p>Source access is unavailable. Reported base values, reference data and derived results are withheld.</p>"
        )
    else:
        p = item["packet"]
        r = item["result"]
        parts += [
            "<h2>"
            + esc(p["name"])
            + "</h2><p>Annual revenue base: USD "
            + esc(p["base"]["value"])
            + "; "
            + esc(p["base"]["start"])
            + " to "
            + esc(p["base"]["end"])
            + ".</p>",
            '<p>Original SEC filing: <a href="'
            + esc(p["report"]["filing_url"])
            + '">'
            + esc(p["report"]["accession"])
            + "</a></p>",
            "<h2>Scenario results</h2><p>Total equity value in USD at "
            + esc(r["target_period_end"])
            + "; undiscounted.</p><table><tr><th>Case</th><th>Projected revenue</th><th>Projected net income</th><th>Equity value</th></tr>",
        ]
        for c in r["cases"]:
            parts.append(
                "<tr>"
                + "".join(
                    "<td>"
                    + esc(c[k] if c[k] is not None else c["reason"] or "Not used")
                    + "</td>"
                    for k in ("name", "revenue", "net_income", "equity_value")
                )
                + "</tr>"
            )
        parts.append("</table>")
        pricing = r.get("price_reference")
        if pricing:
            parts += [
                "<h2>Conditional share price references</h2><p>USD per economically equivalent common share. Horizon: "
                + esc(r["target_period_end"])
                + "; valuation date: " + esc(pricing["valuation_date"])
                + "; annual return assumption: " + esc(pricing["annual_return_percent"])
                + "%; projected diluted shares (millions): " + esc(pricing["projected_shares_millions"])
                + ".</p><p>Share count source and assumptions: " + esc(pricing["share_basis"])
                + ".</p><p>Conditional scenarios, not analyst consensus or trade recommendations.</p>",
                "<table><tr><th>Case</th><th>Scenario horizon price</th><th>Entry reference</th></tr>",
            ]
            for case in r["cases"]:
                price = case["price_reference"]
                parts.append("<tr><th>" + esc(case["name"]) + "</th>" + "".join(
                    "<td>" + esc(price[k] if price[k] is not None else price["reason"]) + "</td>"
                    for k in ("horizon_price", "entry_reference")
                ) + "</tr>")
            parts.append("</table>")
        for c in r["cases"]:
            s = c["sensitivity"]
            parts.append(
                "<h3>"
                + esc(c["name"])
                + " sensitivity</h3><p>Rows: annual revenue growth %. Columns: "
                + esc(s["column"])
                + ".</p><table><tr><th>Growth %</th>"
                + "".join("<th>" + esc(v) + "</th>" for v in s["columns"])
                + "</tr>"
            )
            for row in s["rows"]:
                parts.append(
                    "<tr><th>"
                    + esc(row["growth"])
                    + "</th>"
                    + "".join(
                        "<td>" + esc(cell["equity_value"] or cell["reason"]) + "</td>"
                        for cell in row["cells"]
                    )
                    + "</tr>"
                )
            parts.append("</table>")
            if pricing:
                parts.append("<h4>Per-share sensitivity in USD</h4><p>Each cell: horizon price / entry reference. The same share-count and annual-return assumptions apply.</p><table><tr><th>Growth %</th>" + "".join("<th>" + esc(v) + "</th>" for v in s["columns"]) + "</tr>")
                for row in s["rows"]:
                    parts.append("<tr><th>" + esc(row["growth"]) + "</th>")
                    for cell in row["cells"]:
                        price = cell["price_reference"]
                        value = (price["horizon_price"] + " / " + price["entry_reference"]) if price["horizon_price"] is not None else price["reason"]
                        parts.append("<td>" + esc(value) + "</td>")
                    parts.append("</tr>")
                parts.append("</table>")
        parts += (
            ["<h2>Formulas and limitations</h2><ul>"]
            + ["<li>" + esc(x) + "</li>" for x in r["formulas"] + r["limitations"]]
            + [
                "</ul><h2>Exact source record</h2><pre>"
                + esc(json.dumps(p, indent=2))
                + "</pre>"
            ]
        )
    parts.append("</html>")
    return "fledge-valuation-" + str(scenario_id) + ".html", "".join(parts)
