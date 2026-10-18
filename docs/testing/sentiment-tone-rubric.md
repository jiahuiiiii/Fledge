# Tone rubric for the smaller-task candidate

Prepared 18 October 2026. Prompt `thesis-source-sentiment-tasks-2` remains an
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
the company or reference without supplying the reply's sentiment. An image URL
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

## Teaching, development and acceptance

Five fictional teaching snippets appear in the candidate's instructions.
[Sixteen different authored development cases](../../experiments/sentiment_batching/rubric_cases.json)
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

This uses the distinction between prompt examples and evaluations described in
OpenAI's [prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering)
and [evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices).
