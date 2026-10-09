// Adapted from Kestrel Modal.jsx: portal, Escape dismissal and scroll containment.
// Native dialog additionally provides focus trapping and restores focus on close.
import { useEffect, useRef, useId } from "react";
import { createPortal } from "react-dom";
export default function Modal({
  open,
  onClose,
  title,
  children,
  className = "",
  initialFocus,
  keepMounted = false,
}) {
  const ref = useRef(null),
    id = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (open && !dialog.open) {
      dialog.showModal();
      if (initialFocus) dialog.querySelector(initialFocus)?.focus();
    }
    if (!open && dialog.open) dialog.close();
  }, [open, initialFocus]);
  return createPortal(
    <dialog
      ref={ref}
      className={`modal ${className}`}
      aria-labelledby={id}
      onKeyDown={(event) => {
        if (
          event.key !== "Tab" ||
          event.target.closest("dialog") !== event.currentTarget
        )
          return;
        const controls = [
          ...event.currentTarget.querySelectorAll(
            "button, a[href], input, select, textarea, [tabindex]",
          ),
        ].filter(
          (element) =>
            element.tabIndex >= 0 &&
            !element.disabled &&
            element.getClientRects().length &&
            !element.closest("[inert]"),
        );
        const first = controls[0],
          last = controls.at(-1);
        if (!first) {
          event.preventDefault();
          return;
        }
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      <header>
        <h2 id={id}>{title}</h2>
        <button
          onClick={onClose}
          className="icon-button"
          aria-label="Close dialog"
        >
          ×
        </button>
      </header>
      {(open || keepMounted) && children}
    </dialog>,
    document.body,
  );
}
