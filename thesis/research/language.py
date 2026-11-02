"""A cautious check that a short public post is written in English.

Only text that is clearly not English is turned away: mostly non-Latin
script, a heavy share of accented letters, or a run of words with almost
none of the most common English words. Short or ambiguous text is kept, so a
real English post is never dropped on a guess.
"""
import re

COMMON = frozenset(
    "the be to of and in that have it for not on with you at this but his by from they we say her she or "
    "an will my one all would there their what up out if about who get which go when make can like time just "
    "him know take people into year your good some could them see other than then now look only come its over think "
    "also back after use two how our work first well way even new want because any these give day most is are was "
    "were has had been more very much stock company shares price market earnings".split()
)
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
BASIC_LATIN = re.compile(r"[A-Za-z]")


def looks_english(text):
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 25:
        return True
    basic = sum(1 for c in letters if BASIC_LATIN.match(c))
    # Mostly Cyrillic, CJK, Arabic and so on.
    if basic / len(letters) < 0.6:
        return False
    words = [w.lower() for w in WORD.findall(text)]
    if len(words) < 8:
        return True
    hits = sum(1 for w in words if w in COMMON)
    # English prose is roughly a quarter common words; other Latin-script
    # languages score near zero against this list.
    return hits / len(words) >= 0.15
