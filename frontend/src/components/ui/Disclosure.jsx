import Card from "./Card";
import { ChevronRightIcon } from "./icons";

// Native details keeps keyboard activation and open state browser-owned.
// Pass a custom summary for a rich record; onToggle still receives the native
// event so callers can load children only when explicitly expanded.
export default function Disclosure({
  title,
  description,
  summary,
  indicator = true,
  variant = "panel",
  className = "",
  children,
  ...rest
}) {
  return (
    <Card
      as="details"
      variant={variant}
      className={`ui-disclosure ${className}`}
      {...rest}
    >
      <summary className="ui-disclosure__summary">
        {summary ? (
          <div className="ui-disclosure__content">{summary}</div>
        ) : (
          <span className="ui-disclosure__label">
            <span className="ui-disclosure__title">{title}</span>
            {description && (
              <span className="ui-disclosure__description">{description}</span>
            )}
          </span>
        )}
        {indicator && (
          <span className="ui-disclosure__chevron" aria-hidden="true">
            <ChevronRightIcon />
          </span>
        )}
      </summary>
      <div className="ui-disclosure__body">{children}</div>
    </Card>
  );
}
