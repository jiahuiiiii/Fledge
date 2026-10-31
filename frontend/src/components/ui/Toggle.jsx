import { useId } from "react";
import "./ui.css";

// Fledge's one on/off switch. A native checkbox with role="switch" keeps
// keyboard, form and assistive-technology behaviour; the track and thumb are
// the only styling. Supply a label (or aria-label for the compact, label-less
// form). The caller owns the checked state and change handler. For a choice
// among several options use FilterGroup or Tabs, not a row of toggles.
export default function Toggle({
  checked = false,
  onChange,
  label,
  description,
  disabled = false,
  compact = false,
  className = "",
  id,
  ...rest
}) {
  const generated = useId();
  const controlId = id || generated;
  const descId = description ? `${controlId}-desc` : undefined;
  const classes = ["ui-toggle", compact && "ui-toggle--compact", className]
    .filter(Boolean)
    .join(" ");
  const input = (
    <input
      type="checkbox"
      role="switch"
      id={controlId}
      className="ui-toggle__input"
      checked={checked}
      disabled={disabled}
      aria-describedby={descId}
      onChange={(event) => onChange?.(event.target.checked, event)}
      {...rest}
    />
  );
  if (compact)
    return (
      <span className={classes}>
        {input}
        <span className="ui-toggle__track" aria-hidden="true" />
      </span>
    );
  return (
    <label className={classes} htmlFor={controlId}>
      {input}
      <span className="ui-toggle__track" aria-hidden="true" />
      <span className="ui-toggle__text">
        <span className="ui-toggle__label">{label}</span>
        {description && (
          <small className="ui-toggle__description" id={descId}>
            {description}
          </small>
        )}
      </span>
    </label>
  );
}
