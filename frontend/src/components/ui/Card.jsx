import "./ui.css";

// A Fledge surface. "panel" is the standard block on the page, "inset" sits
// inside a panel, and "flush" is a list row divided by a line. Pass
// as="button" or as="a" with interactive for a card that opens something.
export default function Card({
  variant = "panel",
  as: Tag = "section",
  interactive = false,
  className = "",
  children,
  ...rest
}) {
  const classes = [
    "ui-card",
    `ui-card--${variant}`,
    interactive && "ui-card--interactive",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <Tag
      className={classes}
      {...(Tag === "button" ? { type: "button" } : {})}
      {...rest}
    >
      {children}
    </Tag>
  );
}
