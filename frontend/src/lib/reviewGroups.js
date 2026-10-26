// Weekly review: one group per company, the updates that most need a look first
// (owner feedback 20 Oct 2026: a flat list of identical titles read as empty).
const RANK = { "Bad news": 0, move: 1, "Mixed news": 2, "Good news": 3 };

export function toneClass(tone) {
  return (
    {
      "Good news": "tone-positive",
      "Bad news": "tone-negative",
      "Mixed news": "tone-mixed",
    }[tone] || "tone-neutral"
  );
}

function rank(record) {
  if (record.kind === "move") return RANK.move;
  return RANK[record.detail?.brief?.tone] ?? 4;
}

export function groupByCompany(records) {
  const groups = new Map();
  for (const record of records) {
    const symbol = record.detail?.symbol || "Other";
    if (!groups.has(symbol)) groups.set(symbol, []);
    groups.get(symbol).push(record);
  }
  for (const list of groups.values())
    list.sort(
      (a, b) =>
        rank(a) - rank(b) ||
        String(b.created_at).localeCompare(String(a.created_at)),
    );
  return [...groups.entries()].sort(
    ([a, x], [b, y]) => y.length - x.length || a.localeCompare(b),
  );
}

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

// "42 updates across 3 companies · 3 price moves · 2 bad-news items"
export function weekLine(points) {
  const sum = (key) => points.reduce((total, p) => total + (p[key] || 0), 0);
  return [
    `${plural(sum("total"), "update")} across ${plural(points.length, "company").replace("companys", "companies")}`,
    sum("moves") && plural(sum("moves"), "price move"),
    sum("bad") && plural(sum("bad"), "bad-news item"),
  ]
    .filter(Boolean)
    .join(" · ");
}

// "8 updates · 1 bad · 2 good · 5 neutral or unclear · 1 price move"
export function countsLine(point) {
  return [
    plural(point.total, "update"),
    point.bad && `${point.bad} bad`,
    point.mixed && `${point.mixed} mixed`,
    point.good && `${point.good} good`,
    point.other && `${point.other} neutral or unclear`,
    point.moves && plural(point.moves, "price move"),
  ]
    .filter(Boolean)
    .join(" · ");
}
