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

const NEWS_LINE = {
  good: "News about it is mostly positive",
  bad: "News about it is mostly negative",
  mixed: "News about it is mixed",
};
const SOCIAL_LINE = {
  good: "people online are mostly upbeat",
  bad: "people online are mostly worried",
  mixed: "people online are split",
};

// A few short plain sentences that sum up the saved readings, e.g. "News
// about it is mixed. People online are mostly upbeat. 1 world headline could
// hurt it." It only restates the cards below; it never says what to do.
export function oneLine({ newsTone, newsCount = 0, social = [], links = [] }) {
  const parts = [];
  const newsMood = toneMood(newsTone);
  if (NEWS_LINE[newsMood]) parts.push(NEWS_LINE[newsMood]);
  else if (newsCount)
    parts.push(
      newsCount === 1
        ? "There is 1 recent update, not yet read by AI"
        : `There are ${newsCount} recent updates, not yet read by AI`,
    );
  else parts.push("There’s no recent news saved yet");
  const moods = social.map((s) => toneMood(s.tone)).filter((m) => m !== "none");
  if (moods.length) {
    const mood = moods.every((m) => m === moods[0]) ? moods[0] : "mixed";
    parts.push(SOCIAL_LINE[mood]);
  }
  const count = (effect) => links.filter((l) => l.effect === effect).length;
  const help = count("could_help");
  const hurt = count("could_hurt");
  const either = count("mixed_or_unclear");
  const world = [
    help && `${help} could help it`,
    hurt && `${hurt} could hurt it`,
    either && `${either} could go either way`,
  ].filter(Boolean);
  if (world.length) {
    const total = help + hurt + either;
    const lead = `Of ${total} world headline${total === 1 ? "" : "s"} linked to it, `;
    parts.push(
      total === 1
        ? `1 world headline ${world[0].replace(/^1 /, "")}`
        : lead + (world.length > 1 ? `${world.slice(0, -1).join(", ")} and ${world.at(-1)}` : world[0]),
    );
  }
  // A closing pointer, never a buy/sell call: where to look first.
  const worrying = newsMood === "bad" || hurt > 0;
  const calm = !worrying && (newsMood === "good" || newsMood === "none" && !newsCount) && parts.length > 1;
  if (worrying) parts.push("Worth reading the headlines below before you decide anything");
  else if (calm && NEWS_LINE[newsMood]) parts.push("Nothing in the saved news looks worrying right now");
  return parts.map((p) => p[0].toUpperCase() + p.slice(1) + ".").join(" ");
}
