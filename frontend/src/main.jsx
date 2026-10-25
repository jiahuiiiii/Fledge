import React, { lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import LegalPage from "./components/LegalPage.jsx";
const UiPreview = lazy(() => import("./components/ui/UiPreview.jsx"));
import "./styles/tokens.css";
import "./styles/app.css";
import "./components/ContentFirstLayout.css";
import "./components/ReadingFlow.css";
import "./styles/mobile.css";
import "./styles/header.css";
createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {new URLSearchParams(location.search).has("ui-preview") ? (
      <Suspense fallback={null}>
        <UiPreview />
      </Suspense>
    ) : ["/terms", "/privacy"].includes(location.pathname) ? (
      <LegalPage kind={location.pathname.slice(1)} />
    ) : (
      <App />
    )}
  </React.StrictMode>,
);
