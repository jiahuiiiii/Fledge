# Tone rubric for the smaller-task candidate

Prepared 18 October 2026. Prompt `thesis-source-sentiment-tasks-3` remains an
unapproved-for-activation candidate. It retains GPT-5.4, existing response fields,
source permissions, citation checks, spending ledger and request bounds. There
is no schema, preference, saved-research or live configuration change.

## What is being labelled

Judge the supplied wording about the named company. Relevance and tone are
separate: an explicit question about its named product is relevant even if the
answer or questioner's identity is unknown. A generic sector story can be useful
market context without establishing a company connection or company-tone vote.

For news, label framing about the target. For discussion, label the current
attitude expressed by that message's author. A quote belongs to its speaker;
a reply does not automatically adopt its topic's attitude. Context can resolve
the question and company that a short reply addresses. The reply's own adverse
wording can then establish negative attitude; its length alone is not grounds
for abstention. Do not copy the topic's sentiment into a child. An image URL
does not provide the image's contents. Never reconstruct missing excerpts.

| Label | Evidence required |
| --- | --- |
| Positive | Explicit favourable evaluation or stated favourable target outcome |
| Negative | Explicit adverse evaluation or stated adverse target outcome |
| Mixed | Both opposing evaluations/outcomes apply to the target now |
| Neutral | The relevant meaning is intelligible, without stated direction |
| Unclear | The supplied evidence does not support a reliable target-tone interpretation |

Unrelated/unclear relevance requires unclear tone. A coherent claim can be
neutral even when its factual accuracy is unverified; these labels do not verify
truth. Mixed is not a substitute for uncertainty, missing context, a rival's
contrasting result or a superseded past opinion. In a multi-company comparison,
do not assign unnamed outcomes by title order or outside company knowledge.

## Price conditions and current attitude

Conditional willingness to buy at a lower price, without an explicit evaluation,
is descriptive/neutral. Preserve any explicit current praise or criticism:

| Fictional teaching snippet | Tone | Reason |
| --- | --- | --- |
| “I would buy Aster at a lower price.” | Neutral | An entry condition alone does not establish a favourable/adverse evaluation |
| “I admire Aster; I will wait for a lower price.” | Positive | Current praise, with no explicit opposing evaluation |
| “Aster builds excellent chips but its shares are overpriced.” | Mixed | Explicit current praise and criticism |

Explicit criticism of today's valuation remains negative even if a future lower
price might change the author's view. Hoping that harm is smaller than feared
does not itself supply positive framing. The old conditional-entry owner case
is not relabelled by adopting this clearer candidate convention.

Explicit happiness or desire for a future gain is positive attitude expressed
now. It need not assert that the gain is likely. Distinguish that attitude from
a mechanical entry-price condition or a question about a possible future price.
Tone classification never verifies a forecast.

For news, a reported past share-price gain followed by an unanswered buy/hold
question is neutral when the excerpt supplies no separate evaluation or business
benefit/harm. Keep genuine favourable business outcomes and explicit praise;
an open question does not erase them.

## Owner clarification — 18 October 2026

The owner reaffirmed three exposed examples in a separate follow-up: an adverse
short reply becomes negative when its supplied question makes the target clear;
explicit happiness about a future share-price gain expresses positive attitude;
the past-gain/open-question excerpt is neutral. These choices clarify intended
product behavior, not objective truth or new independent test data.

The private follow-up record is separate from the original 50-label export and
fixed hard-case references. All three answers agree with their earlier reference
tones; none of those originals is replaced or rescored. The two completed
campaign results remain unchanged. A new candidate's quality is unmeasured.

## Teaching, development and acceptance

Eight fictional teaching snippets appear in the candidate's instructions.
[Twenty-three different authored development cases](../../experiments/sentiment_batching/rubric_cases.json)
cover questions, price conditions, attribution, missing information, parent/reply
boundaries, market context and changed views. Their reference answers and
rationales never enter the model's source payload. They are informed by exposed
failure categories, not unseen validation or independent owner judgments.

Offline tests verify complete text/context, bounded requests, accepted reference
response shapes, citation rejection, distinct request identities and historical
label reuse. They cannot establish that GPT-5.4 chooses these answers. A paid
model evaluation requires a separate approved attempt, preserves raw answers and
costs, stops at the first failure and never retries automatically.

Original owner agreement remains **24/50 (48%)**, with **4/6** fixed hard cases.
Those labels and the blind page remain unchanged. A new run over them is a
same-set development comparison, not a fresh 80% acceptance result. A release
quality claim needs a stable rubric and a separately labelled held-out set;
authoring examples or checking our own reference shapes cannot supply that gate.

The prompt revision retains earlier compatible labels with their actual original
prompt/model/call provenance when the existing reliability bridge is enabled.
It changes requests for genuinely fresh or explicitly reread sources; it does
not rewrite historical labels, force a full-pool reread or claim reused items
were evaluated under the new rubric. The legacy live prompt is unchanged.

The explicitly approved **version 2** comparison on 18 October completed 56/56 requests for
US$0.47429, with no failures, repairs, retries or unresolved cost. It did not
improve owner agreement: **24/50 (48%)**, unchanged. Hard cases fell from 4/6 to
**3/6**. Both reference sets stay unchanged. Version 3 reflects the subsequent
owner clarification and has not received a paid evaluation; the candidate remains off.
[Results and limits](../reviews/2026-10-18/sentiment-rubric-candidate.md).

This uses the distinction between prompt examples and evaluations described in
OpenAI's [prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering)
and [evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices).

## Owner decisions and version 4 — 18 October 2026

A full review of all 26 disagreements against this rubric found that most came from labelling conventions rather than model mistakes. Missing conversation context also played a large part. The owner then agreed these rules:

1. **Market-wide news is not company tone.** A market or sector story that doesn't name the company or a concrete relationship is unrelated, even when it is useful background. Price-move explanations (phase 4) are where market context belongs.
2. **Mixed needs both sides stated** about the company now. Only one side stated means positive or negative, not mixed.
3. **Small cases:** a former-employer career mention is unrelated; a description without direction is neutral; an intelligible claim is neutral, not unclear, even when its truth is unverified.

The owner did **not** accept that short Reddit replies should be judged without their conversation. Those replies are answers inside longer discussions. The 50-case test and the blind review page had sent only the topic and the reply (`extras=False`), although threads had 13–30 saved messages. The live app already sends other saved messages from the same discussion, up to 12 KB.

**Version 4** (`thesis-source-sentiment-tasks-4`, still off) changes one rule. A short reply's own favourable **or** adverse wording sets its attitude once context makes the question clear. Explicit agreement adopts the stance it agrees with; a bare laugh does not. One invented teaching example is added. The instruction stays under 6,000 characters (5,973).

The quality runner gains a separate **thread context** plan (`--thread-variant`) that sends the same saved discussion messages as the live app. The review-page evidence shown to the owner is unchanged, and earlier review-context plans keep their exact identity. Hard cases keep their fixed benchmark context.

Still undecided: whether a large bullish trade such as a "yolo" position counts as positive; whether a company CEO criticising others is negative for the company or a neutral report; and what case 08 should be (mixed is not supported). Original owner labels remain unchanged. A separate private reference applies only the agreed rules to the nine cases they cover. Scores against it are same-set development results, not independent validation.

### Thread-context result — 18 October 2026

One approved run of version 4 with full saved thread context completed 56/56 requests for **US$0.5958425**, with no failures, repairs, retries or unresolved cost. Hard cases stayed at **4/6**. Agreement **fell to 22/50** against the original owner labels (from 24/50). Against the agreed-rules reference it is 31/50.

The 19 cases that gained thread messages (11–22 supplied each) now match the owner only 3 times. The model marked 11 of them as unclear relevance, against 5 before, including four replies it previously matched. Reddit RSS does not say which message a reply answers. Given many unordered siblings, the model follows its rule not to infer reply structure from order and abstains. With only the topic, it assumed the reply answered the topic.

**Conclusion:** extra discussion messages without the reply chain make short replies harder to place, not easier. This result does not support sending more unordered thread context. Options are a real reply chain (Reddit's official API, which needs owner setup) or an owner rule that replies in a thread about the company count as about the company unless they clearly discuss something else. Version 4 stays off; no further paid attempt is authorised by this run. Raw requests, responses and the ledger record are in `.local/live-tests/redesign-phase-5-20261018/thread-context-run1/`.

### Agreed-rules reference rescore — 18 October 2026

After re-reading six short replies with their full saved threads, the owner agreed five more reference changes: cases 17, 20, 21, 34 and 38. Case 06 keeps its original label because the thread makes it genuinely ambiguous. The private agreed-rules reference now differs from the original owner labels in 14 of 50 cases. The original labels and their official 24/50 score are unchanged.

Free rescoring of saved predictions (no new AI calls) against that reference:

| Run | Exact agreement |
| --- | --- |
| Original quality prompt, topic-only context | 38/50 |
| Rubric version 2, topic-only context | 37/50 |
| Version 4, full thread context | 32/50 |

Topic-only context is better than unordered full threads. These are same-set development results: the reference was revised after seeing model answers, so it cannot act as independent validation. A release claim still needs a fresh labelled set under these rules. The remaining open rules (large bullish trades, a CEO criticising others, case 08) cover several of the remaining differences.
