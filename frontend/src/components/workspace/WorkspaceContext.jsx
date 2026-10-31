import { createContext, useContext } from "react";

// What every arrangeable widget reads instead of props: the page's data and the
// actions App.jsx owns (open a company, show a source, save a view…). The grid
// can then place any widget anywhere without threading props through it.
const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ value, children }) {
  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("Widgets need a WorkspaceProvider.");
  return value;
}
