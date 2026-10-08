"""Social-specific guidance adapted from Deus pipeline/classifier.py.

Pinned upstream: 74d5aea8b0acf72e1851dfc841f9f1408e9e6609. Its separate Reddit
prompt, community vocabulary and one-result-per-item contract are reused. Its
numeric score, pooled community verdict and trading direction are not adopted.
"""

SOCIAL_GUIDANCE = """
Social discussion interpretation:
Read Reddit, Hacker News and X with their platform context, independently of news framing.
The generic title "X post" supplies no company relevance or opinion; use the original post body.
On investing forums, 'diamond hands', 'tendies', 'to the moon', 'buying the dip',
'bag holder', 'rug pull', 'puts', 'calls', and 'inverse' may describe a position,
slang, a joke, a quote or somebody else's view. They are vocabulary cues, never
a sentiment lookup table. 'I bought puts because I expect AVGO to fall' expresses
a negative investment outlook. 'Are puts a sensible hedge?' is a question, not
evidence of the author's bearish conviction. 'People say to the moon; I disagree'
does not express the quoted optimism. A confident slang-heavy claim can still be
an unsupported opinion. Preserve conditionality, negation, current versus past
positions, author and target. Do not infer stock returns from product complaints.
A source with discovery_match='thread' was found through a company-related parent,
not a direct mention. The reply may be unrelated, neutral or unclear; establish
relevance from its own wording in the supplied context. Do not inherit its parent's
sentiment, treat thread membership as endorsement, or merge multiple authors into
one label. Distinct replies are not necessarily independent people or confirmation.
Do not use popularity to weight a label; no validated vote weights are supplied.
"""
