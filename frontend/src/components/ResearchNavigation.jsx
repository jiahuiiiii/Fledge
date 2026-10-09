const sections = {
  evidence: {
    label: "News & discussion",
    description:
      "Explore the news, discussion and evidence behind the company story.",
    icon: "M3 12h4l3-7 4 14 3-7h4",
  },
  fundamentals: {
    label: "Financials",
    description:
      "Read reported performance and trace the numbers to company filings.",
    icon: "M5 20V10m7 10V4m7 16v-7M3 20h18",
  },
  expectations: {
    label: "Outlook",
    description:
      "Read management guidance, analyst forecasts and expectations reported in the news.",
    icon: "M4 19 10 13l4 3 6-11M14 5h6v6",
  },
  business: {
    label: "Overview",
    description:
      "Understand the business through original company disclosures.",
    icon: "M4 21V7h10v14M14 11h6v10M8 11h2m-2 4h2m-2 4h2M2 21h20",
  },
  valuation: {
    label: "Compare & value",
    description:
      "Compare useful peers, then explore your valuation assumptions.",
    icon: "M12 3v18M17 7H9a3 3 0 0 0 0 6h6a3 3 0 0 1 0 6H7",
  },
};

export default function ResearchNavigation({ selected, onChange, recorded }) {
  const keys = recorded
    ? ["business", "fundamentals", "evidence"]
    : ["business", "fundamentals", "evidence", "expectations", "valuation"];
  return (
    <div className="research-navigation">
      <div
        className="content-tabs"
        role="tablist"
        aria-label="Research views"
        aria-orientation="horizontal"
      >
        {keys.map((key) => (
          <button
            role="tab"
            id={`research-tab-${key}`}
            aria-controls="research-panel"
            aria-selected={selected === key}
            tabIndex={selected === key ? 0 : -1}
            key={key}
            onClick={() => onChange(key)}
            onKeyDown={(event) => {
              const previous = "ArrowLeft";
              const next = "ArrowRight";
              if (![previous, next, "Home", "End"].includes(event.key)) return;
              event.preventDefault();
              const buttons = [
                ...event.currentTarget.parentElement.querySelectorAll(
                  '[role="tab"]',
                ),
              ];
              const index = buttons.indexOf(event.currentTarget);
              const target =
                event.key === "Home"
                  ? 0
                  : event.key === "End"
                    ? buttons.length - 1
                    : (index + (event.key === next ? 1 : -1) + buttons.length) %
                      buttons.length;
              buttons[target].focus();
              buttons[target].click();
            }}
          >
            <svg
              width="19"
              height="19"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d={sections[key].icon} />
            </svg>
            <span>{sections[key].label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function ResearchSectionHeader({ selected }) {
  const section = sections[selected] || sections.evidence;
  return (
    <header className="research-section-heading">
      <h2>{section.label}</h2>
    </header>
  );
}
