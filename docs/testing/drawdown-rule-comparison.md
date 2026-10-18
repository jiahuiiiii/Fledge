# Drawdown candidates on saved prices — 17 October 2026

The owner proposed recent-high drawdowns, reverse rallies, episode follow-ups
and stock-specific volatility scaling. **This is an offline comparison, not an
approved new live rule.** Existing3/2/5thresholds remain selected. CostUS$0,
zero AI/provider calls, no app/DB restart, schema/configuration change or account
write. The user's `app.css` is untouched.

`experiments/soclaas_replay/drawdown_replay.py` has separate capture and comparison
commands. Capture uses a database-enforced repeatable-read read-only transaction,
checks price access and exports no account identities. It refuses to mix multiple
private watchlists without an explicit scope. Comparison reads only frozen files,
records input/index/implementation hashes and refuses to overwrite outputs.

## What was available

Eight company histories were frozen: five enabled watches (AVGO, GOOGL, META,
NVDA, QCOM), plus AMZN for the named sell-off and AAPL/MU for the owner's volatility
example. They contain250–253completed closes over roughly one year, captured as
one split-adjusted vintage each. There are **0missing-session gaps** in these
windows. Sixty prior returns require61prior closes; comparisons therefore share
**189–192scored sessions**, not252scored sessions.

The live database has no saved QQQ history snapshot. An earlier permitted private
probe supplies just **5QQQcloses**, providing3paired scored dates each for AMZN,
GOOGL and NVDA and0for the other histories. A full-year3/2/5comparison is therefore
**unverified**. The main tables compare the stock-only3%day/5%two-session components;
the partial index-gap result and its coverage are recorded separately. No missing
QQQ price is fetched, invented, forward-filled or silently replaced by SPY.

Daily closes also cannot reproduce intraday threshold crossings, live quote
freshness,15-minute checking, actual delivery delay or market-grouped messages.
These counts are **company-day alert opportunities**, not Telegram delivery counts.
Later-captured history is retrospective evidence, not proof it was available then.

## Predeclared candidates and episode semantics

- Fixed entry:7%below the highest close, or7%above the lowest close, in the last
  10completed sessions including today.
- Scaled entry:4times the mean absolute percent close-to-close return over the
  previous60returns, excluding today's return. Compare a2%floor and a7%floor.
  This definition is not standard deviation, ATR or a confidence level.
- Entry thresholds and anchors freeze during an episode. An anchor does not
  expire because it leaves the10-session window.
- Up and down episodes are independent. A summer rally must not mask an October
  pullback. The initial prototype used one direction and was corrected before
  the reported comparison; its private output remains as a diagnostic.
- Follow-ups use5percentage-point excursion steps from the original anchor.
  A jump across several levels produces one event listing all crossed levels.
- Reset is a recovery halfway between the pinned anchor and the worst subsequent
  close. That direction re-arms using prices from the reset onward, preventing an
  instant new alert from the same old high/low. Opposite-direction events can
  still occur; same-company/day opportunities are counted once in union totals.
- A missing trading session resets both episodes and the volatility warm-up.
  Duplicate/unsorted dates, provisional bars, invalid prices and unsupported
  adjustment/calendar bases are rejected or excluded explicitly.

The experiment extends its session-date validation only to October–December2025,
using the [official NYSE calendar](https://ir.theice.com/press/news-details/2024/NYSE-Group-Announces-2025-2026-and-2027-Holiday-and-Early-Closings-Calendar/default.aspx).
The existing2026–2028app calendar supplies later dates. The runtime calendar is
unchanged; the script refuses other unsupported dates.

## Measured comparison

“Additional” means an episode event on a company/date with no stock-only3/5event.
These numbers include rises and falls. They do not classify usefulness.

| Company | Scored sessions |3/5days | Fixed7additional | Scaled4×,2%floor additional | Scaled4×,7%floor additional |
| --- | ---: | ---: | ---: | ---: | ---: |
| AAPL |190|19|8|15|8|
| AMZN |192|28|10|12|10|
| AVGO |190|69|5|3|3|
| GOOGL |192|31|12|11|12|
| META |190|52|9|10|9|
| MU |191|128|2|1|1|
| NVDA |192|48|11|9|9|
| QCOM |189|68|7|9|6|

Mean60-return typical daily moves across the scored dates are1.16%AAPL,
4.17%MU and1.87%NVDA. The stock-only baseline produces2.10opportunities per
21sessions for AAPL and14.07for MU. Adding scaled episodes while retaining that
baseline cannot reduce its volume: the combined MU rate is14.18. This is evidence
of unequal threshold frequency, not proof that every MU alert is noise.

The frozen replay also records the proposed adaptive daily rule: at least
2.5 times the prior 60-return typical move, with a 2% floor. Counting that daily
rule together with scaled drawdown episodes, **without retaining the old 3/5
rules**, gives a different trade-off:

| Company | Scored sessions | Stock-only 3/5 days | Adaptive daily or episode days | Baseline days absent from adaptive candidate |
| --- | ---: | ---: | ---: | ---: |
| AAPL | 190 | 19 | 35 | 3 |
| MU | 191 | 128 | 45 | 84 |
| NVDA | 192 | 48 | 31 | 26 |

These are exact set unions of the already-frozen per-day fields, using the
scaled4×/2%floor episode candidate and its unchanged 5-point follow-ups. They
exclude the index-gap rule because full QQQ coverage is unavailable. An absent
baseline day is not automatically a missed important event; an added adaptive
day is not automatically useful. Both groups need independent review before
replacing any live rule. This comparison supports testing the trade-off, not
selecting the adaptive version solely because MU's count is lower.

The scaled2%floor candidate increases AAPL's additional opportunities from8to15
relative to fixed7. A volatile stock can instead need a higher absolute entry.
Stock-specific scaling is a trade-off, not an automatic improvement on every
metric. The fixed5-point follow-up step also deserves review: MU's scaled candidate
has7entries and32follow-ups. Scaling only the first threshold does not bound all
subsequent alert frequency.

On14October, NVDA closes221.300003against its6October high239.240005: **−7.49875%**.
Fixed7and the scaled threshold **7.03863%** both enter a down episode that day.
The existing daily close move is−3.15946%, also qualifying. On15October the
two-session fall is−4.94049%; there is no new episode step, so no extra alert.
AMZN/GOOGL cross no individual episode threshold on either date. Existing market
grouping can retain them as context; this replay does not invent company triggers
or infer a causal market-wide explanation from co-movement.

AVGO/META/QCOM histories stop before14October, so their October14–15episode
results are unknown here. Do not stitch later quotes onto an earlier adjustment
vintage merely to fill this gap.

## What this does and does not establish

A recent-high rule catches more cumulative moves than fixed1/2-day rules, but its
entry window is still finite. A0.4%daily decline for30sessions loses more than11%
while each10-session excursion stays below7%; both fixed7and3/5remain quiet.
This is an explicit tested limitation, not a claim to catch slides of any shape.

Counts, event dates, monthly unions and the five largest daily moves per company
are retained in the private JSON. The final60scored sessions are reported separately
as chronological validation. Once inspected, they are not an unseen holdout for
further tuning. Choosing numbers and assessing them on the same cases risks
[backtest overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf);
further threshold selection still needs independent review and forward preview.

There is no independent “ordinary volatility” or usefulness label for these
events, so no false-positive rate, best candidate or semantic-quality claim is
made. Moving with QQQ is price context, not proof of the cause. The live preview
is still needed for freshness, timing, grouping, reliability, costs and usefulness.

**Recommendation:** retain fixed and scaled episode candidates for shadow
comparison; define/reset/step behavior before promoting a threshold. Do not change
live thresholds or run two Telegram streams. Any live threshold change still
requires the owner's explicit approval.

Verification:107offline tests pass across the experiment and related replay,
price-rule and price-history suites. Tests cover exact boundaries, slow/gradual
moves, rallies masking pullbacks, multi-level jumps, half recovery/re-arm, expired
anchors, frozen volatility, missing sessions, no lookahead, input identity and
database-enforced read-only capture. No app behavior or frontend changed.

Private evidence: `.local/live-tests/drawdown-comparison-20261017/`; use
`comparison-final`. Its summaries exactly match the corrected `comparison-v2`;
the final output also records the implementation hash. `comparison-v1` is the
superseded single-direction prototype and must not support a product decision.
