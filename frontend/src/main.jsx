import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import LegalPage from "./components/LegalPage.jsx";
import "./styles/tokens.css";
import "./styles/app.css";
import "./components/ContentFirstLayout.css";
import "./components/ReadingFlow.css";
import "./styles/mobile.css";
createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {["/terms", "/privacy"].includes(location.pathname) ? (
      <LegalPage kind={location.pathname.slice(1)} />
    ) : (
      <App />
    )}
  </React.StrictMode>,
);
