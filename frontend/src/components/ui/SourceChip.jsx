import "./ui.css";

// Publisher and date as one link to the original. With no link (or access
// withdrawn) pass onOpen to open the in-app source dialog instead.
export default function SourceChip({
  label,
  date,
  href,
  onOpen,
  className = "",
  ...rest
}) {
  const content = (
    <>
      <span className="ui-source-chip__label">{label}</span>
      {date && <span className="ui-source-chip__date">{date}</span>}
      <span aria-hidden="true">↗</span>
    </>
  );
  const classes = `ui-source-chip ${className}`;
  return href ? (
    <a
      className={classes}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      {...rest}
    >
      {content}
    </a>
  ) : (
    <button type="button" className={classes} onClick={onOpen} {...rest}>
      {content}
    </button>
  );
}
