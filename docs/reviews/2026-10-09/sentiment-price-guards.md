# Sentiment price claims and evidence checks — 9 October 2026

The owner asked to improve sentiment after “AVGO to $340” appeared positive, and
proposed calculated historical price context, conservative label checks and a
frozen real-source regression sample. See the [implemented contract](../../features/sentiment-price-guards.md).

## Actual diagnosis

Read-only inspection found source `a541bedd-ab21-50f4-bd3e-3f1ce168ce3e` in saved
analysis `f159bbba-bbc5-44fd-9c44-27d73af55c39`. Its entire own body is “AVGO to
$340”; its immediate parent is not saved. The timestamp is explicitly a Reddit
feed update. The original v22 call `c41aeb46-4fe0-4f2e-a889-77d1b670ae00` selected
passage p1 and returned positive/expressed_evaluation/opinion/valuation. It received
the company name/symbol and source wording, with no reference price. The earlier
v19 medium-effort call also returned positive. The screenshot faithfully displayed
the saved label; this was not a swapped source or frontend colour bug. The raw
responses contain selected evidence, not a model-authored causal explanation.

No original comment time or compatible price at that time is established by this
record. Today's price cannot repair that uncertainty. Its new-method replay is
unclear, with no fabricated historical return. The owner’s original positive label
remains in its immutable historical reading.

## Implementation and limits

Sentiment v23 adds source-bound structured price extraction to the existing
request. `sentiment_guards.py` reads and pins only a permitted daily capture already
saved by a verified post time, checks company/currency/completed-session/date bounds,
and computes target-versus-close percentages with Decimal. Price arithmetic stays
separate from author attitude; the model does not receive the historical capture.
Unknown post times, missing references, unsupported attribution/ranges/units,
option strikes, provisional bars and later captures do not produce a comparison.

The deterministic rules downgrade bare targets/tickers/numbers, question-only
evidence and inconsistent or unsupported simple price-only views to unclear.
Original AI labels/bases remain visible in the new reading’s check metadata and
unchanged model responses. Final counts use checked labels. Five interpretable
groups plus a strict majority are required for new leaning summaries; the UI shows
the actual numerator/denominator and separate unclear count. Old methods retain
their original threshold/labels/counts. The method identities advance together,
preserving quiet watch-baseline transitions. Access withdrawal also withholds
readings derived from a consumed price source.

No general word-list sentiment classifier is installed. The first experimental
absence-of-evaluation-word gate withheld valid praise and criticism, including a
top-credit-rating reassurance and concerns about financing. Its offline replay
matched 42/50 developer references versus 43/50 for the original outputs. That
failed approach and all seven changed decisions remain in
`offline-reference-first-broad-lexicon.json`. It was removed before installation.
The bounded final replay changes only the bare target and question-only item,
matching 45/50 developer references; five disagreements remain, including mixed
reassurance questions and shared bullish article excerpts. This is **not an
independent accuracy estimate or a live v23 prompt/model evaluation**.

The fifty-case dataset freezes the first fifty social originals in original packet
order, including eligible passages, saved parents, original labels and explicit
developer reference/ambiguity notes. All reference labels await owner validation.
The offline scorer reports confusion tables, missing predictions and disagreements;
it cannot fetch sources or dispatch models. No feedback-button storage or optional
paid disagreement retry was added in this bounded first implementation.

## Verification

Guarded full backend: **1,668 passed / 66 optional skips**. Initial full run retained
two obsolete fixtures: a three-group watch-reversal case and a legacy request-size
fixture too large after the extraction schema expanded. The fixtures were updated
to the new five-group threshold and a genuinely fitting comparison prefix; request
limits and validators were not relaxed. Preserve that initial 1,661-pass/two-failure
log separately.

The final overlapping guard/schema/batching/profile checks passed **96** cases
after sentence-punctuation and instruction-wording refinements. A final **56**-case
guard/reference run verifies that even an erroneously supplied reference cannot
turn a feed-update timestamp into a verified publication time. These counts overlap
and are not additive. Frontend **81** checks, changed-file format, syntax and the
candidate build pass; entry bundle is 498.28kB.

The isolated authored price-guard browser journey passes at 1440/390/320px:
checked label, dated arithmetic/formula, missing original post time, explicit counts,
unchanged legacy label/method notice, focus return, keyboard and reduced motion.
Desktop/phone evidence screenshots were inspected; the Microsoft $360.14 capture
is explicitly authored fixture data, not an actual Microsoft result. One automatic
loading attempt is blocked by the test route; no source/AI request or owner write
is made.

The existing isolated sentiment/watch/history/failure-feedback browser regression
also passes on the final shared candidate, including saved reasoning, grouped
alerts, reload and phone/desktop controls. Its authored writes remain confined to
the disposable test database.

Preserve the first fixture-helper/dictionary-merge failures, mistaken escaped-JSON
assertion, broad-word-list regression, browser session timing, source-button name,
capitalisation and legacy-warning selector failures. The existing sentiment journey
also initially expected the old header progress control; concurrent presentation
work moved it into Research updates. Its test now opens that dialog. Preserve the
initial timeout and the harmless wrong-working-directory editing diagnostic. No
failed candidate was installed.

Evidence: `.local/live-tests/sentiment-price-guards-20261009/`.
Backups: `.local/backups/sentiment-price-guards-20261009/`.

## Installation

The idle app-only restart changed PID 65337 to 26956; the database stayed running.
Backend readiness preceded the guarded atomic index operation, with older assets
retained. A concurrent presentation task had already installed the identical
verified shared frontend: both before/after index hashes are
`871a8809c7da5e5f97155d6f48ebd24410937cdce5ba648c6998f10324e2e069`.
All 43 candidate assets/fonts and local-pitch session readiness were verified.
Full frontend/backend source hashes, installed index and `.env` guards passed.

All **114 table fingerprints are exact**, schema 47 and `.env` unchanged. Actual
workspace readback retains analysis `f159bbba-bbc5-44fd-9c44-27d73af55c39`, with
its original items/summary exactly equal to the saved result. The $340 item is
still the original positive label, without new check metadata; the reading now
has the earlier-method warning. No paid v23 reading was generated or silently
substituted for it.

Ledger exact: US$24.3479945 confirmed + US$1.1624375 reserved, US$4.489568
available of the original US$30, 419 calls/zero running/one unresolved review.
The reservation includes US$0.9156025 historical accounted holds and the separate
US$0.246835 unknown maximum for call `d1cb20a2-71e1-4d6a-b0d5-5de167e47b3e`.
That call was neither retried, reconciled nor released. No model, source, email or
Telegram dispatch was part of this task. Provider restrictions, watch
enrolment/settings and original forecast limitations remain unchanged. Detailed
evidence is in `installation.json`, `before-install.json`, `after-install.json`
and `install.log` beside the preserved test/failure logs.
