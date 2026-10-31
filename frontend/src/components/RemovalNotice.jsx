import { useEffect } from "react";
import { showToast, hideToast } from "./ui";

// The removal message lives in the shared toast; Undo is its action. Clearing
// `company` (undo, restore, or the toast closing) removes it.
export default function RemovalNotice({ company, onUndo, onDismiss }) {
  const id = company ? `removed-${company.id}` : null;
  useEffect(() => {
    if (!id) return undefined;
    showToast(
      `${company.symbol} removed from sidebar. Its watch is off; saved research is kept.`,
      {
        id,
        action: { label: "Undo", onClick: onUndo },
        onClose: onDismiss,
      },
    );
    return () => hideToast(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);
  return null;
}
