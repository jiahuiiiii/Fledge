import "./ui.css";

const HEADINGS = { page: "h1", section: "h2", card: "h3" };

// Title block for a page, a section or a card: small label above, title, one
// line of description and actions on the right. Page and section titles may
// have an icon tile; card titles do not, to keep lists of cards quiet.
// `level` sets the size; `as` changes the heading tag when the page outline
// needs a different level than the visual size; as="span" keeps the whole
// block valid inside a button or link.
export default function SectionHeader({
  title,
  level = "section",
  as,
  icon,
  eyebrow,
  description,
  actions,
  id,
  className = "",
}) {
  const Heading = as || HEADINGS[level];
  const Box = Heading === "span" ? "span" : "div";
  // Spans, not paragraphs, so page-level `p` reading styles cannot resize them.
  const Text = "span";
  return (
    <Box
      className={`ui-section-header ui-section-header--${level} ${className}`.trim()}
    >
      {icon && level !== "card" && (
        <span className="ui-section-header__icon" aria-hidden="true">
          {icon}
        </span>
      )}
      <Box className="ui-section-header__text">
        {eyebrow && (
          <Text className="ui-section-header__eyebrow">{eyebrow}</Text>
        )}
        <Heading id={id} className="ui-section-header__title">
          {title}
        </Heading>
        {description && (
          <Text className="ui-section-header__description">{description}</Text>
        )}
      </Box>
      {actions && <Box className="ui-section-header__actions">{actions}</Box>}
    </Box>
  );
}
