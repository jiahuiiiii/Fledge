// Preview only; the server validates and stores the same original-anchor schedule.
export function eventWindows(event) {
  const step = Number(event.repeat_months || 0),
    count = Number(event.repeat_count ?? 1);
  if (
    ![0, 1, 3, 12].includes(step) ||
    !Number.isInteger(count) ||
    count < 1 ||
    count > 12 ||
    (step === 0) !== (count === 1)
  )
    throw new Error(
      "Choose one window, or 2–12 monthly, quarterly or yearly windows.",
    );
  const shift = (text, months) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(text || ""))
      throw new Error("Choose complete start and deadline dates.");
    const [y, m, d] = text.split("-").map(Number);
    if (
      y < 100 ||
      new Date(Date.UTC(y, m - 1, d)).toISOString().slice(0, 10) !== text
    )
      throw new Error("Use valid calendar dates.");
    const absolute = y * 12 + m - 1 + months,
      year = Math.floor(absolute / 12),
      month = absolute % 12;
    if (year > 9999)
      throw new Error("Use valid calendar dates within year 9999.");
    const last = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
    const targetDay =
      d === new Date(Date.UTC(y, m, 0)).getUTCDate() ? last : Math.min(d, last);
    return new Date(Date.UTC(year, month, targetDay))
      .toISOString()
      .slice(0, 10);
  };
  const windows = [];
  for (let i = 0; i < count; i++) {
    const window_start = shift(event.window_start, step * i),
      deadline = shift(event.deadline, step * i);
    if (
      window_start > deadline ||
      deadline === "9999-12-31" ||
      (i && window_start <= windows[i - 1].deadline)
    )
      throw new Error(
        "Recurring windows must not overlap. Shorten the first window or choose a longer interval.",
      );
    windows.push({ index: i + 1, count, window_start, deadline });
  }
  if (
    (new Date(windows[count - 1].deadline) -
      new Date(windows[0].window_start)) /
      86400000 >
    3650
  )
    throw new Error("Keep the complete schedule within ten years.");
  return windows;
}
