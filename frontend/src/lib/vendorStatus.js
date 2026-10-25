// Plain explanation of what the last FMP similar-companies check did.
// `time` formats an ISO timestamp for display.
export function describeVendorCheck(status, time = (v) => v) {
  if (!status || !status.last_attempt_at) return "FMP has not been asked for similar companies yet.";
  const when = time(status.last_attempt_at);
  const next = status.next_attempt_at ? time(status.next_attempt_at) : null;
  const retry = next ? ` FMP allows one check per hour per company; try again after ${next}.` : "";
  if (status.status === "saved" && status.count > 0)
    return `FMP listed ${status.count} companies at ${when}, but none can be used here (for example another share class of the same issuer).`;
  if (status.error) return `The last check (${when}) did not succeed: ${status.error}.${retry}`;
  if (status.status === "saved") return `The last check (${when}) returned an empty list.${retry}`;
  return `The last check (${when}) saved nothing.${retry}`;
}
