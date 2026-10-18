// The earlier sample behind a company alert is large, so lists omit it and the
// section asks for it when opened. The server applies the same access and
// withdrawal checks; a withheld alert returns no items.
export function savedPreviousSample(alert) {
  return Array.isArray(alert?.previous_items)
    ? { withheld: false, items: alert.previous_items, sources: alert.previous_sources || [] }
    : null;
}

export async function loadPreviousSample(client, id) {
  const result = await client.alertPreviousSample(id);
  if (result?.withheld) return { withheld: true, items: [], sources: [] };
  return {
    withheld: false,
    items: result?.previous_items || [],
    sources: result?.previous_sources || [],
  };
}
