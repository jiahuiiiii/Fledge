import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./style.css";
import "./workspace-layout.css";
import "./readability.css";
import "./interaction.css";
import "./polish.css";
import "./research-flow.css";
import "./research-typography.css";
import "./mobile.css";
import "./source-filters.css";
import "./research-design.css";
import "./reading-journey.css";
createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
