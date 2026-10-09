# Revenue and expense flow

Implemented 9 October 2026 in Financials, inspired by the owner's reference. The flow moved into the Financials reading on the same day; Overview keeps the compact company summary. `sec-income-flow-1` reads retained SEC facts without new data/model requests or changes to monitoring, snapshots or previous financial methods.

Up to five annual and five directly reported quarterly periods are available, plus the latest compatible trailing year using the existing annual + current YTD − prior comparable YTD bridge. Fiscal dates and filing vintages stay explicit; later amendments replace that period's display choice, including a gap if they omit figures.

The diagram follows revenue → gross profit → operating profit → net result, with costs branching out. Connected USD figures share exact dates and reconcile using decimal arithmetic. Missing gross profit, cost of revenue or operating expenses may be explicitly calculated; contradictory reported figures are not replaced. Losses, non-positive revenue, negative costs and unreconciled core figures show signed values without positive-width flows. Net losses or net gains beyond operating profit end the flow at operating profit, preserving available net figures below.

`ProfitLoss` includes non-controlling interests; `NetIncomeLoss` is the parent's result. The selected definition is explicit. **Tax & other net items** is the operating-to-net difference, not a separately reported expense. It may include tax, interest, gains/losses, discontinued operations and non-controlling interests. Operating-expense detail uses reported R&D, combined selling/general/administrative and a labelled calculated remainder. Missing categories are not zero and separate sales/admin costs are never added again to a combined total.

Revenue categories join only when the original-filing reader supplies a reconciled mix matching exact dates, filing URL, concept and total. A single-filing mix never joins a trailing bridge. Dimensions remain separate; more than five categories remain in the complete breakdown. Overlapping geography values are not pooled.

Bands share one scale. Clickable figures show exact inputs, formulas, dates and filing links. Full figures, expenses and definitions are expandable. Phone diagrams scroll inside their container and have an accessible figure list. Keyboard focus, permission checks and reduced motion remain. No chart schema migration. See [verification](../reviews/2026-10-09/revenue-expense-flow.md).
