"""Resolve a quotation to its original text; only whitespace may differ."""

import re


# Shared authoring contract, not a semantic validator. Selected quotations still
# need evaluation: valid IDs alone cannot prove that generated prose follows.
FINDING_GROUNDING = """Evidence selection and writing:
Select the exact passages for a finding before writing its text. Each finding must stand on its OWN selected child passages and separately selected parent passages, not citations elsewhere in the response. Include an antecedent when a quotation says 'it', 'otherwise', 'the company' or 'an argument like that'; if the citation limit prevents a supported explanation, narrow the wording or leave the referent unresolved. Never silently repair a finding with uncited source context.
Preserve the actor, object, timeframe and status of each statement. Do not assign one company's products, figures or actions to another company mentioned in the same sentence. Preserve a current opinion replacing an older opinion, and distinguish 'never' from 'no longer'. Do not add a cause, requirement, future payoff, duration or ending condition merely because it would be plausible. An explanation can describe the expressed attitude or uncertainty without forecasting consequences.
The supplied platform metadata supports platform attribution, not the identity or independence of authors. Parent and child are separate messages; their authors may be the same person. Describe a 'parent message' or 'reply', not 'another commenter' unless supplied identity establishes that distinction. Parent context clarifies the reply but does not turn opinion into official company policy or prove that the child endorses the parent's statements.
Before returning a finding, ensure every substantive clause follows from its own selected evidence, with source-attributed claims still attributed and uncertainty preserved. Omit unsupported clauses rather than expanding them with background knowledge. This applies to explanations and the direct answer as well as individual evidence points."""


def exact_excerpt(quote, text):
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError("An empty quotation is not evidence")
    if quote in text:
        return quote
    # Provider snippets sometimes contain multiple spaces around linked words.
    # Map a whitespace-only match back to the original characters, rather than
    # displaying a model's reformatted text as a verbatim quotation.
    pattern = r"\s+".join(re.escape(p) for p in re.split(r"\s+", quote.strip()))
    match = re.search(pattern, text)
    if not match:
        raise ValueError("Quotation is not in its cited source")
    return match.group(0)


def passage_segments(text, prefix="p", start=0):
    """Stable selections of original text; never generate or shorten a quote."""
    parts = [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+(?=[A-Z“\"])|\n+", text)
        if part.strip()
    ]
    return [dict(id=f"{prefix}{i + start}", quote=part) for i, part in enumerate(parts)]


ELLIPSIS = re.compile(r"\.{3,}|…|\[\s*(?:\.\s*){3,}\]")
# A complete sentence can end inside a closing quotation. Keep a later
# complete sentence separate from an ellipsis in the quoted one. Existing
# unsplit passage IDs stay stable; newly separated parts get explicit suffixes.
QUOTED_END = re.compile(r"(?<=[.!?][\"”’'])\s+(?=[A-Z“\"])")
# A standalone URL after a complete sentence is a separate passage. A
# shortened link must not hide the complete author statement preceding it.
URL_END = re.compile(r"(?<=[.!?])\s+(?=https?://)")


def source_passages(title, text):
    """Keep unsplit IDs, excluding any ellipsis-bearing source passage.

    This is conservative exclusion, not a test that the remaining prose is
    complete. Even a seemingly complete sentence ending 'filing....' is omitted.
    Do not apply this rule to a user's own reasoning segments.
    """
    original = [dict(id="p0", quote=title)]
    for segment in passage_segments(text, start=1):
        parts = [part for quoted in QUOTED_END.split(segment["quote"])
                 for part in URL_END.split(quoted)]
        original.extend(
            dict(
                id=segment["id"] if len(parts) == 1 else f'{segment["id"]}.{i+1}',
                quote=part,
            )
            for i, part in enumerate(parts)
        )
    eligible = [
        p for p in original if p["quote"].strip() and not ELLIPSIS.search(p["quote"])
    ]
    omitted = sum(bool(ELLIPSIS.search(p["quote"])) for p in original)
    return eligible, omitted


def model_source(source, *, include_text=False):
    """Project only eligible source content onto the provider wire contract."""
    passages, omitted = source_passages(source["title"], source["text"])
    projected = {
        key: source[key]
        for key in (
            "id",
            "publisher",
            "published_at",
            "available_at",
            "changed",
            "corrects",
            "kind",
        )
        if key in source
    }
    # A publisher is metadata, not an alternate place to expose a cut-off phrase.
    if isinstance(projected.get("publisher"), str) and ELLIPSIS.search(
        projected["publisher"]
    ):
        projected["publisher"] = None
    projected["title"] = next((p["quote"] for p in passages if p["id"] == "p0"), None)
    projected["omitted_fragment_count"] = omitted
    if include_text:
        projected["text"] = "\n".join(p["quote"] for p in passages if p["id"] != "p0")
    else:
        projected["passages"] = passages
    return projected


def fragment_limitation(count):
    return (
        (
            f" {count} source passage{'s' if count != 1 else ''} containing ellipsis markers "
            f"{'were' if count != 1 else 'was'} excluded from AI input because the context may be unfinished. "
            "Original sources remain available for inspection."
        )
        if count
        else ""
    )
