import Modal from "./Modal";
import { Button } from "./ui";

// A yes/no question in the app's own dialog, in place of the browser's confirm box.
// Cancel is the default focus so Enter never confirms by accident.
export default function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  busy = false,
  danger = false,
  onConfirm,
  onCancel,
}) {
  return (
    <Modal
      open={open}
      onClose={() => !busy && onCancel()}
      title={title}
      className="confirm-dialog"
      initialFocus="[data-confirm-cancel]"
    >
      <div className="confirm-dialog-body">
        <p>{children}</p>
        <div className="confirm-dialog-actions">
          <Button variant="plain" data-confirm-cancel disabled={busy} onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button
            variant="primary"
            danger={danger}
            disabled={busy}
            onClick={onConfirm}
          >
            {busy ? "Working…" : confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
