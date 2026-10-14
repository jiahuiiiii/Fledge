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

// ---- Signals layout (option B): three lights, why, and what happened ----

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

function combinedMood(tones = []) {
  const moods = tones.map(toneMood).filter((m) => m !== "none");
  if (!moods.length) return "none";
  return moods.every((m) => m === moods[0]) ? moods[0] : "mixed";
}

// News light from the saved news reading (or saved updates when unread).
export function newsLight({ tone, counts, analysed = 0, newsCount = 0, latest }) {
  const mood = analysed ? toneMood(tone) : "none";
  const status = analysed ? plainTone(tone) : newsCount ? "Not read yet" : "No news yet";
  const usable = ["positive", "negative", "mixed", "neutral"].reduce(
    (n, k) => n + (counts?.[k] || 0),
    0,
  );
  let reason;
  if (analysed && mood === "good" && usable)
    reason = `${counts.positive || 0} of ${usable} recent articles sound upbeat.`;
  else if (analysed && mood === "bad" && usable)
    reason = `${counts.negative || 0} of ${usable} recent articles sound worried.`;
  else if (analysed && mood === "mixed")
    reason = "Recent articles pull in both directions.";
  else if (analysed) reason = "Too few clear articles to tell which way news leans.";
  else if (newsCount)
    reason = `${plural(newsCount, "saved update")}, not read by AI yet.`;
  else reason = "No company news saved yet.";
  if (latest) reason += ` Latest: “${latest}”.`;
  return { key: "news", title: "News", mood, status, reason };
}

const SOCIAL_STATUS = {
  good: "Mostly upbeat",
  bad: "Mostly worried",
  mixed: "Split",
};
export function socialLight(social = []) {
  const mood = combinedMood(social.map((s) => s.tone));
  const status = social.length
    ? SOCIAL_STATUS[mood] || "Not enough to tell yet"
    : "No reading yet";
  const reason = social.length
    ? social
        .map((s) => `${s.platform}: ${plainTone(s.tone).toLowerCase()}`)
        .join(" · ") + "."
    : "No reading of Reddit, Hacker News or X yet.";
  return { key: "people", title: "People online", mood, status, reason };
}

export function worldLight(linked = [], name = "this company") {
  const links = linked.map((x) => x.link).filter(Boolean);
  const first = (effect) => linked.find((x) => x.link?.effect === effect);
  const hurt = links.filter((l) => l.effect === "could_hurt").length;
  const help = links.filter((l) => l.effect === "could_help").length;
  const either = links.filter((l) => l.effect === "mixed_or_unclear").length;
  const describe = (x) => `${x.link.reason} (“${x.article.headline}”)`;
  if (hurt)
    return {
      key: "world", title: "World", mood: "bad",
      status: hurt === 1 ? "One risk to watch" : `${hurt} risks to watch`,
      reason: describe(first("could_hurt")),
    };
  if (help)
    return { key: "world", title: "World", mood: "good", status: "Could help", reason: describe(first("could_help")) };
  if (either)
    return { key: "world", title: "World", mood: "mixed", status: "Could go either way", reason: describe(first("mixed_or_unclear")) };
  if (linked.length)
    return {
      key: "world", title: "World", mood: "none", status: "In the news",
      reason: `“${linked[0].article.headline}” names ${name}.`,
    };
  return {
    key: "world", title: "World", mood: "none", status: "Nothing linked",
    reason: `No recent world headline is linked to ${name} yet.`,
  };
}

// Short day label in Singapore time: Today, Yesterday, Mon… or 3 Oct.
export function dayLabel(value, now = Date.now()) {
  const t = Date.parse(value);
  if (!Number.isFinite(t)) return "";
  const day = (ms) =>
    new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Singapore" }).format(ms);
  const diff = Math.round((Date.parse(day(now)) - Date.parse(day(t))) / 86400e3);
  if (diff <= 0) return "Today";
  if (diff === 1) return "Yesterday";
  const fmt = diff < 7 ? { weekday: "short" } : { day: "numeric", month: "short" };
  return new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Singapore", ...fmt }).format(t);
}

// Newest company news, posts and linked world headlines, merged by date.
export function whatHappened({ news = [], posts = [], world = [], limit = 6, now = Date.now() }) {
  const rows = [
    ...news.map((s) => ({ id: `n-${s.id}`, kind: "news", text: s.headline, at: s.published_at, item: s })),
    ...posts.map((s) => ({ id: `p-${s.id}`, kind: "post", text: s.headline, at: s.published_at, item: s })),
    ...world.map((x) => ({ id: `w-${x.article.id}`, kind: "world", text: x.article.headline, at: x.article.published_at, url: x.article.url })),
  ].filter((r) => r.text && Number.isFinite(Date.parse(r.at)));
  return rows
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at))
    .slice(0, limit)
    .map((r) => ({ ...r, day: dayLabel(r.at, now) }));
}
