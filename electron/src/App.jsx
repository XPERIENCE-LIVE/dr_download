import React from "react";
import DownloadPanel from "./components/DownloadPanel";
import "./styles/main.css";

export default function App() {
  return (
    <div className="app-container">
      <h1>🎥 Dr. Download 2.0</h1>
      <DownloadPanel />
    </div>
  );
}
