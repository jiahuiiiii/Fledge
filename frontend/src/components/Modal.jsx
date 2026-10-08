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
      {open && children}
    </dialog>,
    document.body,
  );
}
