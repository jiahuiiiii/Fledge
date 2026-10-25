import { Tabs, TabsList, TabsTrigger, SectionHeader } from "./ui";

const sections = {
  summary: {
    label: "Summary",
    description:
      "The price, what the news and people online are saying, and world events that may matter.",
    icon: "M5 4h14v16H5zM8 8h8M8 12h8M8 16h5",
  },
  evidence: {
    label: "News & discussion",
    description:
      "Explore the news, discussion and evidence behind the company story.",
    icon: "M3 12h4l3-7 4 14 3-7h4",
  },
  fundamentals: {
    label: "Financials",
    description:
      "Read reported performance, management guidance and analyst forecasts.",
    icon: "M5 20V10m7 10V4m7 16v-7M3 20h18",
  },
  business: {
    label: "Overview",
    description:
      "See the price, current signals and the business at a glance.",
    icon: "M4 21V7h10v14M14 11h6v10M8 11h2m-2 4h2m-2 4h2M2 21h20",
  },
  valuation: {
    label: "Compare & value",
    description:
      "Compare useful peers, then explore your valuation assumptions.",
    icon: "M12 3v18M17 7H9a3 3 0 0 0 0 6h6a3 3 0 0 1 0 6H7",
  },
};

// Beginner mode keeps two plain views; Pro adds the detailed research tabs.
export function researchTabs({ recorded, beginner }) {
  if (beginner) return ["summary", "evidence"];
  return recorded
    ? ["business", "evidence", "fundamentals"]
    : ["business", "evidence", "fundamentals", "valuation"];
}

export default function ResearchNavigation({
  selected,
  onChange,
  recorded,
  beginner,
}) {
  const keys = researchTabs({ recorded, beginner });
  return (
    <div className="research-navigation">
      <Tabs value={selected} onValueChange={onChange}>
        <TabsList
          variant="line"
          className="content-tabs"
          aria-label="Research views"
        >
          {keys.map((key) => (
            <TabsTrigger
              key={key}
              value={key}
              id={`research-tab-${key}`}
              aria-controls="research-panel"
            >
              {sections[key].label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
    </div>
  );
}

export function ResearchSectionHeader({ selected }) {
  const section = sections[selected] || sections.evidence;
  return (
    <header className="research-section-heading">
      <SectionHeader level="page" as="h2" title={section.label} />
    </header>
  );
}
