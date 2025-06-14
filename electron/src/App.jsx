import React from "react";
import DownloadPanel from "./components/DownloadPanel";
import "./styles/main.css";

export default function App() {
  return (
    <div className="app-container">
      <h1>🎥 PROGRESSIA Media Downloader</h1>
      <DownloadPanel />
    </div>
  );
}