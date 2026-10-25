import { metric, number, previousYear } from "./financialStory.js";

// One number per saved period for the small trend charts. A period without the
// figure is null (a gap in the line), never zero.
export function trendPoints(rows = [], key) {
  return rows.map((row) => {
    if (key === "revenue_growth") {
      const now = number(metric(row, "revenue")?.value);
      const before = number(metric(previousYear(rows, row), "revenue")?.value);
      return now != null && before ? (now / before - 1) * 100 : null;
    }
    return number(metric(row, key)?.value);
  });
}
