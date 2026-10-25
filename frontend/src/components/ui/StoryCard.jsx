import Card from "./Card";
import MetaRow from "./MetaRow";
import Button from "./Button";

// Exact source text is supplied by the caller; this never generates a summary.
// Use href for an original article, onOpen for the existing evidence dialog.
export default function StoryCard({
  title,
  href,
  onOpen,
  meta,
  tags,
  children,
  footer,
  variant = "panel",
  className = "",
  ...rest
}) {
  return (
    <Card
      as="article"
      variant={variant}
      className={`ui-story-card ${className}`}
      {...rest}
    >
      {tags && <div className="ui-story-card__tags">{tags}</div>}
      {meta && <MetaRow>{meta}</MetaRow>}
      <h3 className="ui-story-card__title">
        {href ? (
          <a href={href} target="_blank" rel="noopener noreferrer">
            {title}
            <span className="sr-only"> (opens the original article)</span>
          </a>
        ) : onOpen ? (
          <Button
            variant="plain"
            size="inline"
            onClick={onOpen}
            aria-haspopup="dialog"
          >
            {title}
          </Button>
        ) : (
          title
        )}
      </h3>
      {children}
      {footer && <div className="ui-story-card__footer">{footer}</div>}
    </Card>
  );
}
