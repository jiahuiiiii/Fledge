import { useState } from "react";
import Modal from "./Modal";

export default function EvidenceButton({
  title = "Evidence",
  children,
  className = "",
  label = "Evidence",
}) {
  const [open, setOpen] = useState(false);
  return (
    <span className={`evidence-control ${className}`}>
      <button
        type="button"
        className="source-link evidence-button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
      >
        {label}
      </button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={title}
        className="evidence-dialog"
      >
        {children}
      </Modal>
    </span>
  );
}
