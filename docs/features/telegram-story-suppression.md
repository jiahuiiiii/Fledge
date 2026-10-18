# One story per account over 24 hours

Prepared 17 October 2026 on `codex/redesign-phase-5`. **Not installed or enabled;
phase 5 is not done.** New additive migration066 is unapplied live. No app/DB
process, environment, account preference, saved research or installed asset is
changed by this preparation. No paid AI call or original-source request is used.

## Send intent and the evidence actually shown

`telegram_story_claims` is an append-only, forced-RLS journal. Each entry belongs
to an account, outbox delivery and send attempt, and contains a hashed story key
and intent time. It stores neither message text nor a chat destination. The
database accepts claims only for the matching `sending` attempt, and rejects
preview company/move publications. Claims commit with send intent before HTTP,
under the existing per-account cross-process Telegram lock.

The formatter reports primary evidence that actually survived its message bound.
An omitted third source or a whole excerpt that did not fit is not marked sent.
Private idea interpretations retain their original alert identity and ratings;
filtering changes only a temporary message copy. Saved publications and frozen
recap memberships remain exact. Price triggers and monitored-condition changes
use their event identity: their cited news/filings are context and cannot suppress
a genuinely different numeric event.

## Which reports count as the same story

News uses the saved content identity, validated repeat ancestors, and a canonical
article URL. Canonicalization removes fragments and known tracking fields only;
article identifiers and other query values remain. Invalid/private links and a
publisher homepage without an article query do not supply an article identity.
A validated repeat can connect different outlets. Similar wording alone does not
merge stories. Distinct social posts remain separate opinions, even with the same
words; repeated versions of the same saved post can be recognized.

A cited addition/contradiction, or new numeric/status wording against a saved
same-URL comparison with newly cited evidence, retains a separate update identity.
An old quote cannot manufacture that exception. An actual update also reserves
the article URL for later cosmetic repeats; its own eligibility checks do not let
the previous article's URL block the new development. These are bounded evidence
checks, not proof that a model correctly understood every development.

Filtering applies across company and private-idea publications, across watched
companies in the same account, and between immediate messages and recaps. Inside
a recap, only complete displayed blocks reserve keys. Duplicate members are
omitted, the original full recap remains available, and numbered rating buttons
still point to the correct original member. Immediate messages retain qualifying
high-importance evidence; removing an already-covered high item cannot promote a
remaining low/medium item into an immediate message.

## Delivery state, retries and expiry

Only the outbox's current attempt supplies active claims. Confirmed delivery
reserves a story for 24 hours after `sent_at`; an uncertain/interrupted send is
treated as possibly delivered, for 24 hours after its intent. Exact expiry is
half-open: a claim stops blocking at the 24-hour boundary. Failed, skipped or
cancelled attempts do not block a later eligible publication.

A known rate-limit rejection may still be queued. A competing copy waits for
that reservation rather than being permanently discarded before the original
attempt resolves. Deferral makes no HTTP call and consumes no send attempt. The
original retry ignores its own claims, rechecks evidence, and records the new
shown set. If attempt2 succeeds with different evidence, attempt1's rejected,
omitted evidence does not become falsely marked as delivered. Existing bounded
known-rejection retries and no-resend-after-uncertainty rules remain.

Older ordinary deliveries without claims are checked read-only through the same
bounded formatter and currently accessible evidence/revisions; no historical
claims are inserted. This compatibility check is limited to1,000recent records;
overflow refuses preparation explicitly. Withdrawn, changed-private or malformed
old interpretations cannot establish a reliable reconstructed shown set and are
not used. Exact new-journal coverage therefore must not be inferred for every
unverifiable pre-install message.

## Activation and rollback

Ordinary shadow/comparison delivery is unchanged while actual severity routing is
off. Actual severity mode enables the guard with its existing explicit activation
start. A prepared actual-policy recap keeps its guard and records claims even if
ordinary severity routing is subsequently rolled back; its separate approved
recap-delivery switch still controls whether it can send. Cost notices and test
messages do not claim news stories. No live approval is inferred from this code.

Turning routing off restores the ordinary pipeline without deleting claims or
changing research. Turning recap delivery off is rechecked before dispatch.
Current source permissions and private revisions are still checked before any
message. Nothing here starts a model request, source refresh or paid retry.

## Verification and limits

Final affected routing/recap/guard suites:152pass, including41new guard cases.
The full offline run passes2,547tests with93optional skips. It collected before
three late regression cases and the final non-article URL-key guard; the subsequent
152affected checks cover final code. Earlier broader related suites:249pass,
preceding the final additions. Tests use authored sources and a mocked bot, with a real
throwaway database for ownership, append-only and send-intent checks. They cover
both immediate/recap directions, two watched companies, same-message repeats,
account isolation, exact expiry, pending/rejected/uncertain states, changed retry
members, concurrent workers, before-HTTP durability and message bounds.

Private evidence: `.local/live-tests/redesign-phase-5-20261017/story-guard-prepared/`.
Frontend202tests and scratch build pass; no frontend source was changed.
Initial fixture/context and missing-keyword test-hook diagnostics are retained.
User `app.css` remains byte-for-byte exact. Cost US$0; no live message was sent.

This does **not** establish semantic duplicate detection for every paraphrase,
actual zero duplicates over10UStrading days, or the phase5noise/quality gates.
Independent seven-day replay remains0/7; owner labels0/50 and new-prompt hard
cases0/6. Quality/cost evaluation, live choices, installation, shadow period and
forward outcome measurements remain outstanding. No phase is marked done.
