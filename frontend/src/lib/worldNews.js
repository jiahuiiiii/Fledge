// Presentation helpers for the World view. Theme tags and mentions come from the
// server; these only filter and word them.

export const EFFECT_LABELS = {
  could_help: "could help",
  could_hurt: "could hurt",
  mixed_or_unclear: "could go either way",
};

// "all", "mine" (names or may affect a watchlist company) or a theme id.
export function filterArticles(articles = [], filter = "all") {
  if (filter === "all") return articles;
  if (filter === "mine")
    return articles.filter(
      (a) => a.mentions?.length > 0 || a.links?.length > 0,
    );
  return articles.filter((a) => a.themes?.includes(filter));
}

export function themeCounts(articles = [], themes = []) {
  return themes.map((theme) => ({
    ...theme,
    count: articles.filter((a) => a.themes?.includes(theme.id)).length,
  }));
}

// Why the AI check button is unavailable, or null when it can run.
export function checkBlocker(page) {
  if (!page) return "Loading world news…";
  if (!page.companies?.length)
    return "Add a company to your watchlist to check headlines against it.";
  if (!page.articles?.length) return "Refresh world news first.";
  if (!page.ai?.available)
    return "needs AI, which isn’t switched on in this copy of Fledge.";
  return null;
}
