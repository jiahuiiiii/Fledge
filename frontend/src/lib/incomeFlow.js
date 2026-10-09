const numeric = (value) => {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) && Math.abs(n) <= 1e16 ? n : null;
};

// Join only reconciled original categories from the exact same filing/period.
// Trailing bridges span filings and cannot borrow a single-period segment mix.
export function matchingMix(period, groups = []) {
  if (!period || period.kind === "trailing") return [];
  const revenue = period.metrics.find((row) => row.key === "revenue");
  if (revenue?.inputs.length !== 1) return [];
  const input = revenue.inputs[0];
  return groups.filter(
    (group) =>
      group.chartable &&
      group.start === period.start &&
      group.end === period.end &&
      group.url === input.filing_url &&
      group.concept?.split(":").at(-1) === input.concept &&
      group.total === revenue.value &&
      group.members.every(
        (row) => numeric(row.value) != null && numeric(row.value) >= 0,
      ),
  );
}

export function flowLayout(period, mix) {
  if (!period?.chartable) return null;
  const rows = period.nodes;
  const revenue = rows.find((row) => row.key === "revenue");
  if (
    !revenue ||
    numeric(revenue.value) <= 0 ||
    rows.some((row) => numeric(row.value) == null || numeric(row.value) < 0)
  )
    return null;
  const scale = 190 / numeric(revenue.value);
  const sources = mix
    ? [...mix.members]
        .sort((a, b) => Number(b.value) - Number(a.value))
        .map((row, i) => ({
          ...row,
          key: `source-${i}`,
          column: -1,
          tone: "revenue",
          group: mix,
        }))
    : [];
  // Large sets remain readable in the separate reported-breakdown view.
  const included = sources.length <= 5 ? sources : [];
  const offset = included.length ? 1 : 0;
  const columns = Math.max(...rows.map((row) => row.column)) + offset + 1;
  const step = 225;
  const positions = new Map();
  const nodes = [...included, ...rows].map((row) => {
    const column = row.column + offset;
    const y = positions.get(column) ?? 105;
    const height = numeric(row.value) * scale;
    positions.set(column, y + height + 110);
    return { ...row, x: 20 + column * step, y, height, width: 12 };
  });
  const byKey = new Map(nodes.map((row) => [row.key, row]));
  const outgoing = new Map(),
    incoming = new Map();
  const links = [
    ...included.map((row) => ({
      source: row.key,
      target: "revenue",
      value: row.value,
    })),
    ...period.links,
  ].map((link) => {
    const source = byKey.get(link.source),
      target = byKey.get(link.target);
    const height = numeric(link.value) * scale;
    const sy = source.y + (outgoing.get(source.key) || 0);
    const ty = target.y + (incoming.get(target.key) || 0);
    outgoing.set(source.key, (outgoing.get(source.key) || 0) + height);
    incoming.set(target.key, (incoming.get(target.key) || 0) + height);
    const x1 = source.x + 12,
      x2 = target.x,
      mid = (x1 + x2) / 2;
    return {
      ...link,
      tone: target.tone,
      path: `M${x1},${sy} C${mid},${sy} ${mid},${ty} ${x2},${ty} L${x2},${ty + height} C${mid},${ty + height} ${mid},${sy + height} ${x1},${sy + height} Z`,
    };
  });
  return {
    nodes,
    links,
    width: (columns - 1) * step + 220,
    height: Math.max(...nodes.map((row) => row.y + row.height)) + 30,
  };
}

export const shortLabel = (value, size = 25) => {
  const lines = [""];
  for (const word of value.split(" ")) {
    const last = lines.length - 1;
    if (lines[last] && lines[last].length + word.length + 1 > size)
      lines.push(word);
    else lines[last] += `${lines[last] ? " " : ""}${word}`;
  }
  return lines;
};
