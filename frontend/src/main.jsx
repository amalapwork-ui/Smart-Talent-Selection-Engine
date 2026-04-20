import React from "react";
import ReactDOM from "react-dom/client";
import { Toaster } from "react-hot-toast";
import "./index.css";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: { fontSize: "14px", maxWidth: "380px" },
        success: { iconTheme: { primary: "#22c55e", secondary: "#fff" } },
        error: { iconTheme: { primary: "#ef4444", secondary: "#fff" } },
      }}
    />
  </React.StrictMode>
);
