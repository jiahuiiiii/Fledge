// Plain-language copy for the four investor types. The type itself is worked
// out on the server (thesis/investor_type.py) from the five quiz answers.
export const INVESTOR_TYPES = {
  starting_out: {
    name: "Just starting out",
    short: "You’re learning before you invest, which is a good place to start.",
    about:
      "There’s no rush. Following a few companies you know is a simple way to learn how news moves prices.",
    watch:
      "The common trap is jumping in because of one exciting post. Look at the good and the bad news first.",
    fledge:
      "Fledge explains each company’s news, what people online are saying and world events in plain words.",
  },
  long_term: {
    name: "Long-term investor",
    short: "You buy businesses you believe in and hold them for years.",
    about:
      "Day-to-day price moves matter less to you than how the business does over time.",
    watch:
      "The common trap is holding on after the reason you bought has stopped being true.",
    fledge:
      "Fledge keeps your own reason next to the news, so you can see whether the story still holds.",
  },
  steady_builder: {
    name: "Steady builder",
    short: "You invest a little at a time, often through funds or ETFs.",
    about:
      "You prefer a simple routine over trying to pick the perfect moment.",
    watch:
      "The common trap is dropping your routine after one scary headline, or not knowing what’s inside the funds you own.",
    fledge:
      "Fledge explains big world news, like rate cuts, wars and oil, in plain words, so you can see what it might mean for you.",
  },
  swing_trader: {
    name: "Swing trader",
    short: "You look for moves that play out over days or weeks.",
    about:
      "You often act around news, company results or a trend you can see building.",
    watch:
      "Short moves are hard to predict and trading costs add up. Deciding before you buy what would make you sell helps you stay honest.",
    fledge:
      "Fledge shows what the news and people online are saying right now, and which world events could touch your companies.",
  },
  active_trader: {
    name: "Active trader",
    short: "You trade often, sometimes within the same day, and may use options.",
    about:
      "Speed matters to you, and you follow prices closely.",
    watch:
      "Studies of frequent traders find most lose money after costs, and options can lose their whole value. Know how much you can afford to lose.",
    fledge:
      "Fledge is a research tool, not a trading screen. Use it to check the story behind a move. Pro tools in Account add financials and charts.",
  },
};

export const typeName = (key) => INVESTOR_TYPES[key]?.name || "";
