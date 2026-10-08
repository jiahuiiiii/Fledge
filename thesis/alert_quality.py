"""Frozen source/expectation scoring for development, never an accuracy claim.

No acquisition, model call, account mutation or publication occurs in this module.
The runner uses the application's existing request, validation and budget layer.
"""

import hashlib
from html import escape
from collections import Counter
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal
from .providers.ledger import canonical

ALERTS = {"supports", "challenges", "risk", "answers"}
RELATIONS = ALERTS | {"context", "unclear", "unrelated"}


class Expected(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    allowed: dict[str, list[str]]
    rationale: str = Field(min_length=10)

    @model_validator(mode="after")
    def nonempty(self):
        if not self.allowed or any(not values for values in self.allowed.values()):
            raise ValueError("Each expected field needs an explicit allowed set.")
        return self


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9_-]+$", max_length=80)
    task: Literal["sentiment", "relevance"]
    packet: dict
    expected: list[Expected] = Field(min_length=1, max_length=16)
    description: str = Field(min_length=10)
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def coverage(self):
        sources = self.packet.get("sources", [])
        ids = [s["id"] for s in sources]
        if len(ids) != len(set(ids)) or Counter(ids) != Counter(
            e.source_id for e in self.expected
        ):
            raise ValueError("Exactly one expectation is required per distinct source.")
        if self.task == "sentiment":
            labels = [s["label"] for s in sources]
            if len(labels) != len(set(labels)):
                raise ValueError("Source labels must be distinct.")
            fields = {
                "relevance": {"relevant", "unrelated", "unclear"},
                "sentiment": {"positive", "negative", "mixed", "neutral", "unclear"},
                "statement": {
                    "reported_development",
                    "opinion",
                    "rumour",
                    "question",
                    "unclear",
                },
            }
        else:
            fields = {"relation": RELATIONS}
        for e in self.expected:
            if any(
                k not in fields or not set(v) <= fields[k] for k, v in e.allowed.items()
            ):
                raise ValueError("Unexpected classification field or value.")
            if self.task == "relevance":
                statuses = {v in ALERTS for v in e.allowed["relation"]}
                if len(statuses) != 1:
                    raise ValueError(
                        "An alert expectation must unambiguously require or suppress an alert."
                    )
        return self


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def request(case):
    from .research import idea_alerts, sentiment

    module = sentiment if case.task == "sentiment" else idea_alerts
    body = module.request_for(case.packet)
    if digest(body) != case.request_sha256:
        raise ValueError(
            "The frozen request changed. Create a separately labelled retest manifest."
        )
    return module, body


def score(case, result, gate=None):
    """Count only explicit prewritten criteria; do not infer semantic truth.

    gate is the sentiment relevance output for a paired pipeline check. Quiet
    items excluded by that gate stay quiet. A missed relevant item is counted
    as a pipeline false negative even if the direct relevance prompt found it.
    """
    expected = {e.source_id: e for e in case.expected}
    actual = result["items"]
    if Counter(i["source_id"] for i in actual) != Counter(expected.keys()):
        raise ValueError("Result coverage does not match the frozen expected sources.")
    if gate is not None and set(gate) != set(expected):
        raise ValueError("The relevance gate must cover the same sources exactly.")
    checks, failures, confusion = 0, [], Counter()
    for item in actual:
        e = expected[item["source_id"]]
        for field, allowed in e.allowed.items():
            checks += 1
            if item.get(field) not in allowed:
                failures.append(
                    dict(
                        source_id=e.source_id,
                        field=field,
                        expected=allowed,
                        actual=item.get(field),
                        rationale=e.rationale,
                    )
                )
        if case.task == "relevance":
            wanted = all(v in ALERTS for v in e.allowed["relation"])
            produced = item["relation"] in ALERTS and (
                gate is None or gate[item["source_id"]] == "relevant"
            )
            confusion[
                ("true_" if wanted == produced else "false_")
                + ("positive" if produced else "negative")
            ] += 1
    return dict(
        case=case.id,
        task=case.task,
        item_count=len(actual),
        criteria=checks,
        matched=checks - len(failures),
        failures=failures,
        alert_confusion=(
            {
                k: confusion[k]
                for k in (
                    "true_positive",
                    "false_positive",
                    "true_negative",
                    "false_negative",
                )
            }
            if case.task == "relevance"
            else None
        ),
        gate_applied=gate is not None,
        limitation="Developer-authored expectations on a selected sample. Matching labels and exact quotations do not establish explanation truth, population accuracy, prospective delay or user value.",
    )


def review_html(manifest, results):
    """Inert local review packet; expected answers are disclosed in details."""
    esc = lambda value: escape(str(value), quote=True)
    parts = [
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'>",
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'\">",
        "<title>Thesis alert quality review</title><style>body{font:16px/1.6 system-ui;max-width:1000px;margin:auto;padding:24px;color:#17282c}section{border:1px solid #bcc9c9;padding:20px;margin:18px 0}blockquote{border-left:3px solid #6a9292;margin-left:0;padding-left:16px}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}h2{margin-top:40px}a{color:#00646b}</style>",
        "<h1>Alert quality review</h1><p>Development review of actual stored public sources and authored research situations. This is not investment advice, an independent benchmark or participant feedback.</p>",
        "<p>Review the source and explanation before opening the expected labels. Check company identity, time, attribution, whether the connection is meaningful, and whether you would want the alert. Record disagreements separately; do not rewrite frozen expectations.</p>",
        "<p>" + esc(manifest["description"]) + "</p>",
    ]
    for raw in manifest["cases"]:
        case = Case.model_validate(raw)
        if case.id not in results:
            continue
        result = results[case.id]
        scored = score(case, result)
        source_map = {s["id"]: s for s in case.packet["sources"]}
        expected = {e.source_id: e for e in case.expected}
        parts.append(
            "<h2>" + esc(case.id) + "</h2><p>" + esc(case.description) + "</p>"
        )
        if case.task == "relevance":
            parts.append(
                "<h3>Authored saved question</h3><blockquote>"
                + esc(case.packet["question"])
                + "</blockquote>"
            )
            parts.append(
                "<h3>Authored saved reasoning</h3><blockquote>"
                + esc(case.packet["reasoning"])
                + "</blockquote>"
            )
        parts.append(
            "<p>Source cutoff: "
            + esc(case.packet["cutoff"])
            + ". Prompt: "
            + esc(result["prompt_version"])
            + ".</p>"
        )
        for item in result["items"]:
            source = source_map[item["source_id"]]
            parts.append(
                "<section><h3>"
                + esc(source["title"])
                + "</h3><p>"
                + esc(source["publisher"])
                + " · "
                + esc(source["published_at"])
                + "</p><blockquote>"
                + esc(source["text"])
                + "</blockquote>"
            )
            parts.append(
                "<p><b>Model: "
                + esc(item.get("relation", item.get("sentiment")))
                + "</b> — "
                + esc(item["explanation"])
                + "</p>"
            )
            if item.get("reasoning_quote"):
                parts.append(
                    "<p>Linked saved sentence:</p><blockquote>"
                    + esc(item["reasoning_quote"])
                    + "</blockquote>"
                )
            parts.append(
                "<p>Selected source passages:</p>"
                + "".join(
                    "<blockquote>" + esc(c["quote"]) + "</blockquote>"
                    for c in item["citations"]
                )
            )
            if item.get("question_quote"):
                parts.append(
                    "<p>Linked saved question:</p><blockquote>"
                    + esc(item["question_quote"])
                    + "</blockquote>"
                )
            e = expected[item["source_id"]]
            parts.append(
                "<details><summary>Frozen expected labels and rationale</summary><pre>"
                + esc(canonical(e.allowed))
                + "</pre><p>"
                + esc(e.rationale)
                + "</p></details></section>"
            )
        parts.append(
            "<details><summary>Mechanical label comparison</summary><p>"
            + esc(scored["matched"])
            + " / "
            + esc(scored["criteria"])
            + " prewritten field checks matched. This is not an accuracy rate.</p><pre>"
            + esc(canonical(scored["failures"]))
            + "</pre></details>"
        )
    return "".join(parts) + "</html>"
