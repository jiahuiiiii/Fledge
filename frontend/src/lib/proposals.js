export function combineSuggestions(proposals) {
  if (!proposals.length) throw new Error("Choose a suggestion to review.");
  const first = proposals[0],
    result = structuredClone(first.base),
    seen = new Set();
  for (const p of proposals) {
    if (
      p.status !== "pending" ||
      !p.candidate ||
      p.base_version_id !== first.base_version_id ||
      p.instrument_id !== first.instrument_id ||
      p.snapshot_id !== first.snapshot_id
    )
      throw new Error(
        "These suggestions no longer share the same current idea and evidence. Request fresh suggestions.",
      );
    const key =
      p.kind === "reasoning"
        ? "reasoning"
        : p.target_condition_id
          ? p.kind + ":" + p.target_condition_id
          : null;
    if (key && seen.has(key))
      throw new Error("Choose one proposed change per existing condition.");
    if (key) seen.add(key);
    if (p.kind === "reasoning") {
      result.question = p.candidate.question;
      result.reasoning = p.candidate.reasoning;
    } else {
      const field = p.kind === "numeric" ? "conditions" : "events";
      if (p.operation === "add") {
        const ids = new Set(p.base[field].map((c) => c.condition_id));
        result[field].push(
          ...p.candidate[field].filter((c) => !ids.has(c.condition_id)),
        );
      } else if (p.operation === "remove")
        result[field] = result[field].filter(
          (c) => c.condition_id !== p.target_condition_id,
        );
      else
        result[field] = result[field].map((c) =>
          c.condition_id === p.target_condition_id
            ? p.candidate[field].find((n) => n.condition_id === c.condition_id)
            : c,
        );
    }
  }
  if (result.conditions.length > 4 || result.events.length > 3)
    throw new Error(
      "Choose fewer suggestions: an idea supports four numerical and three event conditions.",
    );
  return result;
}

// What a suggestion would do, ignoring when it was made. Two suggestions with
// the same key ask for the same thing.
export function suggestionKey(p) {
  const d = p.proposed?.definition || p.proposed || {};
  const what =
    p.kind === "reasoning"
      ? "reasoning"
      : p.kind === "numeric"
        ? [d.metric, d.role, d.operator, d.period_type].join("/")
        : [d.role, (d.description || "").trim().toLowerCase()].join("/");
  return [p.kind, p.operation, p.target_condition_id || "", what].join("|");
}

// Newest first in, newest of each kind out. Older repeats and anything that
// repeats a still-open suggestion are left out of the history.
export function splitSuggestions(proposals) {
  const open = [];
  const openKeys = new Set();
  for (const p of proposals.filter((q) => q.status === "pending")) {
    const key = suggestionKey(p);
    if (openKeys.has(key)) continue;
    openKeys.add(key);
    open.push(p);
  }
  const past = [];
  const pastKeys = new Set();
  for (const p of proposals.filter((q) => q.status !== "pending")) {
    const key = suggestionKey(p);
    if (p.status !== "approved" && (openKeys.has(key) || pastKeys.has(key)))
      continue;
    pastKeys.add(key);
    past.push(p);
  }
  return { open, past };
}

// The condition ids a suggestion would add, so a threshold typed on its card
// reaches the right row.
export function addedConditionIds(p) {
  if (p.kind !== "numeric" || p.operation !== "add") return [];
  const have = new Set((p.base?.conditions || []).map((c) => c.condition_id));
  return (p.candidate?.conditions || [])
    .map((c) => c.condition_id)
    .filter((id) => !have.has(id));
}
