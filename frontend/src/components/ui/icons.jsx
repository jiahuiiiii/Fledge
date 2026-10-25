// Small line icons for icon tiles and buttons. Drawn for Fledge on a 24-unit
// grid; they inherit the text colour.
function Icon({ children }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
    >
      {children}
    </svg>
  );
}

export const PlusIcon = () => (
  <Icon>
    <path d="M12 5v14M5 12h14" />
  </Icon>
);
export const ChevronRightIcon = () => (
  <Icon>
    <path d="m9 6 6 6-6 6" />
  </Icon>
);
export const BellIcon = () => (
  <Icon>
    <path d="M6 16v-5a6 6 0 0 1 12 0v5l1.5 2h-15z" />
    <path d="M10 20.5a2 2 0 0 0 4 0" />
  </Icon>
);
export const ChartIcon = () => (
  <Icon>
    <path d="M4 19h16" />
    <path d="m5 15 4-5 4 3 6-7" />
  </Icon>
);
export const ExternalIcon = () => (
  <Icon>
    <path d="M14 5h5v5M19 5l-8 8" />
    <path d="M18 14v4a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4" />
  </Icon>
);
export const BookmarkIcon = () => (
  <Icon>
    <path d="M7 4h10v16l-5-3.5L7 20z" />
  </Icon>
);
export const TrashIcon = () => (
  <Icon>
    <path d="M5 7h14M10 7V5h4v2M7 7l1 12h8l1-12" />
  </Icon>
);
export const GridIcon = () => (
  <Icon>
    <path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" />
  </Icon>
);
export const NewsIcon = () => (
  <Icon>
    <path d="M5 5h11v14H6a1 1 0 0 1-1-1z" />
    <path d="M16 9h3v9a1 1 0 0 1-1 1h-2M8 9h5M8 12h5M8 15h3" />
  </Icon>
);

export const LightbulbIcon = () => (
  <Icon>
    <path d="M9 18h6M10 21h4" />
    <path d="M9 15c0-2-3-3-3-6a6 6 0 0 1 12 0c0 3-3 4-3 6z" />
  </Icon>
);

export const GlobeIcon = () => (
  <Icon>
    <circle cx="12" cy="12" r="9" />
    <ellipse cx="12" cy="12" rx="4" ry="9" />
    <path d="M3 12h18M5 6h14M5 18h14" />
  </Icon>
);
export const RefreshIcon = () => (
  <Icon>
    <path d="M20 7v5h-5M4 17v-5h5" />
    <path d="M5.5 8a7 7 0 0 1 11.6-3L20 8M4 16l2.9 3A7 7 0 0 0 18.5 16" />
  </Icon>
);
export const UserIcon = () => (
  <Icon>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21v-2a8 8 0 0 1 16 0v2" />
  </Icon>
);
