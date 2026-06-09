import React from "react";
import ReactDOM from "react-dom/client";
import { ThemeModeProvider } from "./themeMode";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeModeProvider>
      <App />
    </ThemeModeProvider>
  </React.StrictMode>
);
