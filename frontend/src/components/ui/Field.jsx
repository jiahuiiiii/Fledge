import { Children, cloneElement, isValidElement, useId } from "react";
import "./ui.css";

// A form field: one label, its control, and an optional hint or error, wired
// together for assistive technology. Wrap a single control (Select, Combobox,
// an input or textarea); Field injects the id, aria-describedby, aria-invalid
// and required state so callers do not repeat that plumbing per page. The
// caller still owns the control's value, change and validation.
export default function Field({
  label,
  hint,
  error,
  required = false,
  className = "",
  children,
  ...rest
}) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  const control = Children.only(children);
  const wired = isValidElement(control)
    ? cloneElement(control, {
        id: control.props.id || id,
        "aria-describedby":
          [control.props["aria-describedby"], describedBy]
            .filter(Boolean)
            .join(" ") || undefined,
        "aria-invalid": error ? true : control.props["aria-invalid"],
        required: required || control.props.required,
      })
    : control;
  const classes = ["ui-field", error && "ui-field--error", className]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={classes} {...rest}>
      {label && (
        <label className="ui-field__label" htmlFor={control.props?.id || id}>
          {label}
          {required && (
            <span className="ui-field__required" aria-hidden="true">
              {" *"}
            </span>
          )}
        </label>
      )}
      {wired}
      {hint && !error && (
        <p className="ui-field__hint" id={hintId}>
          {hint}
        </p>
      )}
      {error && (
        <p className="ui-field__error" id={errorId} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
