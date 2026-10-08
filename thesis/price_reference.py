"""Conditional per-share arithmetic, with explicit dilution and return assumptions."""

from datetime import date
from decimal import Decimal, localcontext
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .research.sec.performance import decimal_text

METHOD = "equity-multiples-per-share-1"


class PriceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valuation_date: date
    projected_shares_millions: Decimal = Field(
        ge=Decimal("0.000001"), le=Decimal("10000000"),
        max_digits=14, decimal_places=6, allow_inf_nan=False,
    )
    annual_return_percent: Decimal = Field(
        ge=0, le=100, max_digits=9, decimal_places=6, allow_inf_nan=False,
    )
    share_basis: str = Field(min_length=8, max_length=1200)

    @field_validator("share_basis")
    @classmethod
    def meaningful_basis(cls, value):
        value = value.strip()
        if len(value) < 8:
            raise ValueError("Explain the share count, share classes and dilution assumption.")
        return value


def prices(equity_value, target, spec):
    """A terminal-price-only return model; no interim distribution is inferred."""
    days = (target - spec.valuation_date).days
    reason = None
    if equity_value is None:
        reason = "This case has no usable equity value, so per-share prices are unavailable."
    elif days <= 0:
        reason = "The scenario horizon has already ended on this valuation date. Choose a later horizon."
    with localcontext() as ctx:
        ctx.prec = 28
        years = Decimal(days) / Decimal("365.25")
        terminal = (
            Decimal(equity_value) / (spec.projected_shares_millions * 1_000_000)
            if reason is None else None
        )
        entry = (
            terminal / ((1 + spec.annual_return_percent / 100) ** years)
            if terminal is not None else None
        )
        return dict(
            horizon_price=decimal_text(terminal) if terminal is not None else None,
            entry_reference=decimal_text(entry) if entry is not None else None,
            years_from_valuation_date=decimal_text(years),
            reason=reason,
        )


def extend(result, spec):
    target = date.fromisoformat(result["target_period_end"])
    result["method"] = METHOD
    result["price_reference"] = dict(
        **spec.model_dump(mode="json"),
        unit="USD_per_economically_equivalent_common_share",
        day_count="Actual days / 365.25",
    )
    for case in result["cases"]:
        case["price_reference"] = prices(case["equity_value"], target, spec)
        for row in case["sensitivity"]["rows"]:
            for cell in row["cells"]:
                cell["price_reference"] = prices(cell["equity_value"], target, spec)
    result["formulas"] += [
        "Scenario horizon price = total company equity value / (assumed projected diluted shares in millions × 1,000,000)",
        "Years remaining = actual days from valuation date to scenario horizon / 365.25",
        "Entry reference = scenario horizon price / (1 + chosen annual return / 100)^years remaining",
    ]
    result["limitations"] = [
        v for v in result["limitations"] if not v.startswith("Values cover total company equity.")
    ] + [
        "Per-share prices are conditional scenarios from your assumptions, not analyst consensus, fair-value certification or buy/sell recommendations.",
        "Use the total projected diluted common-share count across economically equivalent classes, on one consistent split basis. A single class count, depositary receipt ratio or unequal economic rights requires a separate model; this tool does not convert them.",
        "The share count is your horizon assumption, not an automatically verified current count. Include expected issuance, buybacks, options and other dilution; the same assumption applies to every case and sensitivity cell.",
        "The entry reference discounts only the hypothetical horizon price at your chosen annual return. Dividends, interim distributions, taxes and transaction costs are excluded; this is not a full discounted-cash-flow valuation.",
        "The valuation date is a reference date for this calculation, not a historical backtest. Saved inputs are not automatically adjusted for later splits, corporate actions or new information.",
    ]
    return result
