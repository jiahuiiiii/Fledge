const numeric = (value) => {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) && Math.abs(n) <= 1e16 ? n : null;
};

// Join only reconciled original categories from the exact same filing/period.
// Trailing bridges require their complete, unchanged three-input basis.
export function matchingBreakdowns(period, groups = []) {
  if (!period) return [];
  const revenue = period.metrics.find((row) => row.key === "revenue");
  if (period.kind === "trailing") {
    const basis = (inputs) =>
      JSON.stringify(
        (inputs || []).map((row) => [
          row.filing_url,
          row.concept,
          row.start,
          row.end,
          row.value,
        ]),
      );
    return groups.filter(
      (group) =>
        group.period_id === period.id &&
        group.calculated &&
        group.start === period.start &&
        group.end === period.end &&
        group.total === revenue?.value &&
        basis(group.revenue_inputs) === basis(revenue?.inputs),
    );
  }
  if (revenue?.inputs.length !== 1) return [];
  const input = revenue.inputs[0];
  return groups.filter(
    (group) =>
      group.start === period.start &&
      group.end === period.end &&
      group.url === input.filing_url &&
      group.concept?.split(":").at(-1) === input.concept &&
      group.total === revenue.value,
  );
}

export function matchingMix(period, groups = []) {
  return matchingBreakdowns(period, groups).filter(
    (group) =>
      group.chartable &&
      group.members.every(
        (row) => numeric(row.value) != null && numeric(row.value) >= 0,
      ),
  );
}

export function flowLayout(period, mix, availableWidth = 0) {
  if (!period?.chartable) return null;
  const rows = period.nodes;
  const revenue = rows.find((row) => row.key === "revenue");
  if (
    !revenue ||
    numeric(revenue.value) <= 0 ||
    rows.some((row) => numeric(row.value) == null || numeric(row.value) < 0)
  )
    return null;
  const sources =
    mix?.chartable &&
    mix.members.every(
      (row) => numeric(row.value) != null && numeric(row.value) >= 0,
    )
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
  // Labels sit beside source bars, so five-country disclosures fit without
  // either stretching the SVG or suppressing their links to total revenue.
  const included = sources.length <= 6 ? sources : [];
  let scale = 190 / numeric(revenue.value);
  const sourceHeight = (s) =>
    included.reduce((h, row) => h + Math.max(56, numeric(row.value) * s), 0) +
    Math.max(0, included.length - 1) * 12;
  if (sourceHeight(scale) > 420) {
    let low = 0,
      high = scale;
    for (let i = 0; i < 32; i++) {
      const mid = (low + high) / 2;
      if (sourceHeight(mid) > 420) high = mid;
      else low = mid;
    }
    scale = low;
  }
  const offset = included.length ? 1 : 0;
  const inset = included.length ? 176 : 0;
  const columns = Math.max(...rows.map((row) => row.column)) + offset + 1;
  const step = Math.max(225, (availableWidth - 220 - inset) / (columns - 1));
  const positions = new Map();
  let sourceY = 28;
  const nodes = [...included, ...rows].map((row) => {
    const column = row.column + offset;
    const height = numeric(row.value) * scale;
    if (row.group) {
      const slot = Math.max(56, height);
      const node = {
        ...row,
        x: 196,
        y: sourceY + (slot - height) / 2,
        height,
        width: 12,
        labelX: 20,
        labelY: sourceY + slot / 2,
        hitY: sourceY,
        hitHeight: slot,
      };
      sourceY += slot + 12;
      return node;
    }
    const y = positions.get(column) ?? 95;
    positions.set(column, y + height + 80);
    return { ...row, x: 20 + inset + column * step, y, height, width: 12 };
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
    width: (columns - 1) * step + 220 + inset,
    height:
      Math.max(sourceY - 12, ...nodes.map((row) => row.y + row.height)) + 30,
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
