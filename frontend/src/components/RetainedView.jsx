import { useRef } from "react";

// Mount on first visit, then retain this company's view state between tabs.
// The parent unmounts these views whenever the selected company changes.
export default function RetainedView({ active, children }) {
  const visited = useRef(false);
  if (active) visited.current = true;
  if (!visited.current) return null;
  return (
    <div className="retained-view" hidden={!active}>
      {children}
    </div>
  );
}
