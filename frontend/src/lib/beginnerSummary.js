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
  if (Number(pct) === 0) return { price, move: "flat since the last close", mood: "none" };
  const up = quote.change_percent > 0;
  return {
    price,
    move: `${up ? "up" : "down"} ${pct}% since the last close`,
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
  const hurt = links.filter((l) => l.effect === "could_hurt").length;
  const help = links.filter((l) => l.effect === "could_help").length;
  const either = links.filter((l) => l.effect === "mixed_or_unclear").length;
  if (links.length) {
    const status = [
      help && `${help} could help`,
      hurt && `${hurt} could hurt`,
      either && `${either} either way`,
    ]
      .filter(Boolean)
      .join(", ");
    const mood = help && hurt ? "mixed" : hurt ? "bad" : help ? "good" : "mixed";
    return {
      key: "world", title: "World", mood, status, hurt,
      reason: hurt
        ? `${hurt === 1 ? "One world event" : `${hurt} world events`} could hurt ${name}. Read why below.`
        : `No linked world event looks likely to hurt ${name}.`,
    };
  }
  if (linked.length)
    return {
      key: "world", title: "World", mood: "none", status: "In the news", hurt: 0,
      reason: `“${linked[0].article.headline}” names ${name}.`,
    };
  return {
    key: "world", title: "World", mood: "none", status: "Nothing linked", hurt: 0,
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

// ---- Concrete lights: real headlines grouped by how they sound ----

// Split saved news or posts by their saved tone. Unrated items (no AI reading
// yet, or unclear) stay visible as "not rated".
export function groupByTone(items = []) {
  const groups = { good: [], bad: [], mixed: [], neutral: [], unrated: [] };
  for (const item of items) {
    if (item.tone === "positive") groups.good.push(item);
    else if (item.tone === "negative") groups.bad.push(item);
    else if (item.tone === "mixed") groups.mixed.push(item);
    else if (item.tone === "neutral") groups.neutral.push(item);
    else groups.unrated.push(item);
  }
  return groups;
}

// "2 good, 1 bad, 3 just facts" — counts instead of a vague mood word.
export function countLabel(groups, { good = "good", bad = "bad", neutral = "neutral" } = {}) {
  const parts = [
    groups.good.length && `${groups.good.length} ${good}`,
    groups.bad.length && `${groups.bad.length} ${bad}`,
    groups.mixed.length && `${groups.mixed.length} mixed`,
    groups.neutral.length && `${groups.neutral.length} ${neutral}`,
  ].filter(Boolean);
  if (parts.length) return parts.join(", ");
  if (groups.unrated.length) return `${groups.unrated.length} new, not rated yet`;
  return "Nothing saved yet";
}

export function countMood(groups) {
  const good = groups.good.length;
  const bad = groups.bad.length;
  if (good && bad) return "mixed";
  if (bad) return "bad";
  if (good) return "good";
  if (groups.mixed.length) return "mixed";
  return "none";
}

// What the mix of headlines means, in words a beginner can act on safely.
export function newsMeaning(groups) {
  const good = groups.good.length;
  const bad = groups.bad.length;
  if (good && bad)
    return "There is good and bad news. Read both sides below.";
  if (bad)
    return "The recent news is bad for the company. Read why below; bad news doesn’t always mean the price falls.";
  if (good)
    return "The recent news is good for the company. Good news doesn’t guarantee the share price goes up.";
  if (groups.mixed.length || groups.neutral.length)
    return "The recent news mostly reports what happened, without clearly good or bad news for the company.";
  if (groups.unrated.length)
    return "Fledge hasn’t rated these yet. Read the headlines and judge for yourself.";
  return "No company news is saved yet.";
}

export function peopleMeaning(groups) {
  const up = groups.good.length;
  const down = groups.bad.length;
  const both = groups.mixed.length;
  const tail = " Online posts are opinions, not facts.";
  if (up && down)
    return (up > down
      ? "Most posts are upbeat, but some are worried."
      : down > up
        ? "Most posts are worried, but some are upbeat."
        : "Posts are split between upbeat and worried.") + tail;
  if (down) return "Posts sound worried." + tail;
  if (up) return "Posts sound upbeat. Online hype can be wrong.";
  if (both) return "Posts see both good and bad sides." + tail;
  if (groups.unrated.length) return "These posts haven’t been rated yet." + tail;
  return "No posts about this company are saved yet.";
}
