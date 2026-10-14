// Plain-language wording for the Beginner summary. Everything here rewords
// saved readings; nothing new is inferred, scored or recommended.

const TONE_WORDS = {
  "positive leaning": "Mostly positive",
  "negative leaning": "Mostly negative",
  mixed: "Mixed",
  "mixed / balanced": "Mixed",
  neutral: "Mostly neutral",
  "thin sample": "Not enough to tell yet",
};

export function plainTone(tone) {
  if (!tone) return "Not checked yet";
  return TONE_WORDS[tone] || tone[0].toUpperCase() + tone.slice(1);
}

// "good" | "bad" | "mixed" | "none" — only for colouring the label.
export function toneMood(tone) {
  if (!tone) return "none";
  if (/positive/.test(tone)) return "good";
  if (/negative/.test(tone)) return "bad";
  if (/mixed/.test(tone)) return "mixed";
  return "none";
}

const ITEM_TONE = {
  positive: "Positive",
  negative: "Negative",
  mixed: "Mixed",
  neutral: "Neutral",
};
export const itemTone = (tone) => ITEM_TONE[tone] || null;

const PLATFORM = { reddit: "Reddit", hackernews: "Hacker News", x: "X" };
export const platformName = (platform) => PLATFORM[platform || "reddit"] || platform;

// Price move in words, e.g. "up 1.2% today".
export function priceLine(quote) {
  if (!quote || !(quote.price > 0)) return null;
  const price = `$${Number(quote.price).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
  if (quote.change_percent == null) return { price, move: null, mood: "none" };
  const pct = Math.abs(Number(quote.change_percent)).toFixed(1);
  if (Number(pct) === 0) return { price, move: "flat in the last session", mood: "none" };
  const up = quote.change_percent > 0;
  return {
    price,
    move: `${up ? "up" : "down"} ${pct}% in the last session`,
    mood: up ? "good" : "bad",
  };
}

// Social tone across platforms: one line per platform that has a reading.
export function socialTones(scopes = []) {
  return scopes
    .filter((s) => s.scope !== "news" && s.analysed > 0)
    .map((s) => ({ platform: platformName(s.scope), tone: s.tone }));
}

// World headlines that name this company or were linked to it by the AI check.
export function worldForCompany(page, companyId, limit = 3) {
  if (!page?.articles) return { linked: [], bigPicture: [] };
  const linked = page.articles
    .map((article) => ({
      article,
      link: article.links?.find((l) => l.company_id === companyId) || null,
      named: article.mentions?.includes(companyId) || false,
    }))
    .filter((x) => x.link || x.named)
    .slice(0, limit);
  const shown = new Set(linked.map((x) => x.article.id));
  // Otherwise, the newest rate and conflict headlines give the big picture.
  const bigPicture = page.articles
    .filter(
      (a) =>
        !shown.has(a.id) &&
        a.themes?.some((t) => ["rates", "geopolitics", "trade"].includes(t)),
    )
    .slice(0, linked.length ? 0 : 2);
  return { linked, bigPicture };
}
