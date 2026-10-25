import React from "react";
import { createRoot } from "react-dom/client";
import FinancialRecovery from "../../frontend/src/components/FinancialRecovery";
import "../../frontend/src/styles/tokens.css";
import "../../frontend/src/styles/app.css";
import "../../frontend/src/components/ContentFirstLayout.css";
import "../../frontend/src/components/ReadingFlow.css";
import "../../frontend/src/styles/mobile.css";
import "../../frontend/src/components/FinancialsPage.css";

createRoot(document.getElementById("root")).render(
  <div className="app-shell" style={{ display: "block", padding: 16 }}>
    <div className="research-content">
      <button role="tab" aria-selected="true">
        Financials
      </button>
      <h2>Financials</h2>
      <FinancialRecovery instrumentId="authored" />
    </div>
  </div>,
);
