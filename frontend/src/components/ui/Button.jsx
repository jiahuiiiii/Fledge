import "./ui.css";

// Fledge's one button. Pick a variant instead of styling buttons per page:
// primary for the main action, secondary for a second choice, tertiary for
// light actions in the accent colour, plain for neutral ones. Sizes are md,
// sm and inline (inside a sentence). A button with only an icon needs an
// aria-label. With href it renders a link that looks the same.
export default function Button({
  variant = "secondary",
  size = "md",
  danger = false,
  icon,
  iconEnd,
  href,
  type = "button",
  className = "",
  children,
  ...rest
}) {
  const iconOnly = !children && Boolean(icon || iconEnd);
  const classes = [
    "ui-button",
    `ui-button--${variant}`,
    `ui-button--${size}`,
    danger && "ui-button--danger",
    iconOnly && "ui-button--icon-only",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  const content = (
    <>
      {icon && (
        <span className="ui-button__icon" aria-hidden="true">
          {icon}
        </span>
      )}
      {children}
      {iconEnd && (
        <span className="ui-button__icon" aria-hidden="true">
          {iconEnd}
        </span>
      )}
    </>
  );
  return href ? (
    <a className={classes} href={href} {...rest}>
      {content}
    </a>
  ) : (
    <button type={type} className={classes} {...rest}>
      {content}
    </button>
  );
}
