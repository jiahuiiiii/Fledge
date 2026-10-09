export function preferPriceRead(current, next) {
  if (!next?.data?.available || current?.data?.symbol !== next.data.symbol)
    return next;
  const previous = Date.parse(current?.data?.snapshot?.retrieved_at);
  const incoming = Date.parse(next.data.snapshot?.retrieved_at);
  return previous > incoming
    ? { ...next, data: { ...next.data, snapshot: current.data.snapshot } }
    : next;
}

export function priceRefreshDelay(data, now = Date.now()) {
  if (!data?.available || !data.configured || data.error) return null;
  const next = Date.parse(data.next_refresh_at);
  return Math.max(0, (Number.isFinite(next) ? next : now) - now);
}

export function latestPriceQuote(market, history) {
  const quote = history?.snapshot?.series?.latest_quote;
  if (!history?.available || !quote) return null;
  return Date.parse(quote.quoted_at) >=
    (Date.parse(market?.quote?.quote?.quoted_at) || 0)
    ? quote
    : null;
}

const finite = (value) =>
  value == null ||
  value === "" ||
  typeof value === "boolean" ||
  !Number.isFinite(Number(value))
    ? null
    : Number(value);
export function quoteMovement(market, history) {
  const latest = latestPriceQuote(market, history);
  if (!latest) {
    const quote = market?.quote?.quote;
    const change = finite(quote?.change);
    return change == null
      ? null
      : { change, percent: finite(quote.change_percent), referenceDate: null };
  }
  // Same-snapshot completed closes only; the displayed reference date does
  // not assume complete exchange-calendar coverage or a current-day quote.
  const series = history.snapshot.series;
  const price = finite(latest.price),
    time = Date.parse(latest.quoted_at);
  if (
    !(price > 0) ||
    !Number.isFinite(time) ||
    series.omitted_sessions !== 0 ||
    !["regular session", "pre-market", "after-hours"].includes(latest.session)
  )
    return null;
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/New_York",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    })
      .formatToParts(time)
      .map((part) => [part.type, part.value]),
  );
  const sessionDate = `${parts.year}-${parts.month}-${parts.day}`;
  const closes = (series.bars || [])
    .filter(
      (bar) =>
        bar.provisional === false &&
        /^\d{4}-\d{2}-\d{2}$/.test(bar.date) &&
        (bar.date < sessionDate ||
          (latest.session === "after-hours" && bar.date === sessionDate)),
    )
    .sort((a, b) => a.date.localeCompare(b.date));
  const previous = closes.at(-1),
    close = finite(previous?.close);
  if (!(close > 0)) return null;
  const change = price - close;
  return {
    change,
    percent: (change / close) * 100,
    referenceDate: previous.date,
  };
}
