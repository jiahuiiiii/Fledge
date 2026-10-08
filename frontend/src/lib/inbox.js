const relations = {
  supports: "May support your reasoning",
  challenges: "May challenge your reasoning",
  risk: "Risk to investigate",
  answers: "Evidence toward your question",
};

export function inboxSummary(record) {
  const d = record.detail;
  if (d.withheld)
    return {
      title: "Source access changed",
      text: "Evidence and interpretation are withheld. Your review history is preserved.",
    };
  if (record.kind === "company")
    return {
      title: record.title,
      text: d.payload.items?.[0]?.explanation || d.payload.reason,
    };
  if (record.kind === "condition")
    return { title: record.title, text: d.question };
  const noteworthy = d.items.filter((i) => relations[i.relation]);
  const kinds = [...new Set(noteworthy.map((i) => i.relation))];
  return {
    title:
      kinds.length === 1
        ? relations[kinds[0]]
        : "Connections to your saved reasoning",
    text: noteworthy[0]?.explanation || d.question,
    question: d.question,
  };
}

export function recordKey(record) {
  return `${record.kind}:${record.id}`;
}
