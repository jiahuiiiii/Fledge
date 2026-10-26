import { Toast } from "./ui";

export default function RemovalNotice({ company, onUndo, onDismiss }) {
  return (
    <Toast
      id={company?.id}
      message={company && `${company.symbol} removed from sidebar. Its watch is off; saved research is kept.`}
      action={{ label: "Undo", onClick: onUndo }}
      onDismiss={onDismiss}
    />
  );
}
