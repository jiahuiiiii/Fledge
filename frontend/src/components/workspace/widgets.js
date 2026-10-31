// Every arrangeable block, per page. This registry is the single source of
// default positions: a saved layout is merged with it on every read, so new
// widgets appear at their default place and retired ids are dropped.
// Keep the ids in step with WIDGETS in thesis/workspace_layouts.py.
//
// Columns: lg 12, md 10, sm 6. Heights (h, in grid rows) are only a starting
// size; each widget grows to fit its content, so nothing is cut off.
import {
  SummaryNews,
  SummaryPeople,
  SummarySignals,
  SummaryView,
  SummaryWorld,
} from "./SummaryWidgets";
import { HomeCompanies, HomePortfolio, HomeWelcome } from "./HomeWidgets";

const full = (y, h) => ({
  lg: { x: 0, y, w: 12, h },
  md: { x: 0, y, w: 10, h },
  sm: { x: 0, y, w: 6, h },
});
// Side by side on wide boards (as the summary was before), stacked otherwise.
const half = (side, y, h, stackedY) => ({
  lg: { x: side * 6, y, w: 6, h },
  md: { x: 0, y: stackedY, w: 10, h },
  sm: { x: 0, y: stackedY, w: 6, h },
});

export const WIDGETS = {
  overview: [
    {
      id: "signals",
      title: "Price and signals",
      component: SummarySignals,
      minW: 4,
      default: full(0, 60),
    },
    {
      id: "news",
      title: "News",
      component: SummaryNews,
      minW: 3,
      default: half(0, 60, 160, 60),
    },
    {
      id: "people",
      title: "People online",
      component: SummaryPeople,
      minW: 3,
      default: half(1, 60, 160, 220),
    },
    {
      id: "world",
      title: "World",
      component: SummaryWorld,
      minW: 3,
      default: half(0, 220, 60, 380),
    },
    {
      id: "view",
      title: "Your view",
      component: SummaryView,
      minW: 3,
      default: half(1, 220, 60, 440),
    },
  ],
  home: [
    {
      id: "welcome",
      title: "Welcome",
      component: HomeWelcome,
      minW: 4,
      default: full(0, 40),
    },
    {
      id: "portfolio",
      title: "Your list today",
      component: HomePortfolio,
      minW: 4,
      default: full(40, 160),
    },
    {
      id: "companies",
      title: "Your companies",
      component: HomeCompanies,
      minW: 4,
      default: full(200, 200),
    },
  ],
};
