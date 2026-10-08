export const hiddenCompaniesKey = "thesis.sidebar.hidden-companies.v1";
export function parseHiddenCompanies(raw) {
  try {
    const values = JSON.parse(raw || "[]");
    return Array.isArray(values)
      ? [
          ...new Set(
            values.filter(
              (value) =>
                typeof value === "string" && /^[a-f0-9-]{36}$/i.test(value),
            ),
          ),
        ]
      : [];
  } catch {
    return [];
  }
}
