// Every arrangeable block, per page. This registry is the single source of
// default positions: a saved layout is merged with it on every read, so new
// widgets appear at their default place and retired ids are dropped.
// Keep the ids in step with WIDGETS in thesis/workspace_layouts.py.
//
// Columns: lg 12, md 10, sm 6. Heights (h, in grid rows) are only a starting
// size; each widget grows to fit its content, so nothing is cut off.
//
// optional: starts hidden, listed under "Sections you can add" in Arrange.
// modes: detail modes that offer it ("explain" Beginner, "data" Pro).
// when(context): offered only if true for this page (e.g. not for the
// fictional practice companies, which have no real prices or filings).
import {
  SummaryNews,
  SummaryPeople,
  SummarySignals,
  SummaryView,
  SummaryWorld,
} from "./SummaryWidgets";
import {
  CompanyActivity,
  CompanyBusiness,
  CompanyChart,
  CompanyGlance,
  CompanyTargets,
  CompanyWatch,
} from "./CompanyWidgets";
import {
  HomeAlerts,
  HomeCompanies,
  HomeInbox,
  HomePortfolio,
  HomeWelcome,
  HomeWorld,
} from "./HomeWidgets";

const real = (context) => !context.recorded;
// Before the first company is added, the home shows only the welcome card and
// its "Add a company" button, not empty company sections.
const hasCompanies = (context) => context.catalogue?.length > 0;
const PRO = ["data"];

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
    {
      id: "glance",
      title: "At a glance",
      component: CompanyGlance,
      minW: 4,
      optional: true,
      modes: PRO,
      when: real,
      default: half(0, 300, 60, 520),
    },
    {
      id: "activity",
      title: "Latest activity",
      component: CompanyActivity,
      minW: 3,
      optional: true,
      when: real,
      default: half(1, 300, 60, 580),
    },
    {
      id: "chart",
      title: "Price chart",
      component: CompanyChart,
      minW: 4,
      optional: true,
      when: real,
      default: full(360, 160),
    },
    {
      id: "business",
      title: "The business",
      component: CompanyBusiness,
      minW: 4,
      optional: true,
      when: real,
      default: full(700, 160),
    },
    {
      id: "targets",
      title: "Analyst price targets",
      component: CompanyTargets,
      minW: 4,
      optional: true,
      modes: PRO,
      when: real,
      default: half(0, 860, 120, 860),
    },
    {
      id: "watch",
      title: "News watch",
      component: CompanyWatch,
      minW: 3,
      optional: true,
      when: real,
      default: half(1, 860, 60, 980),
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
      when: hasCompanies,
      default: full(40, 160),
    },
    {
      id: "companies",
      title: "Your companies",
      component: HomeCompanies,
      minW: 4,
      when: hasCompanies,
      default: full(200, 200),
    },
    {
      id: "alerts",
      title: "Today’s alerts",
      component: HomeAlerts,
      minW: 3,
      optional: true,
      default: half(0, 400, 80, 400),
    },
    {
      id: "inbox",
      title: "Updates to review",
      component: HomeInbox,
      minW: 3,
      optional: true,
      default: half(1, 400, 80, 480),
    },
    {
      id: "world",
      title: "World headlines",
      component: HomeWorld,
      minW: 4,
      optional: true,
      default: full(560, 100),
    },
  ],
};
