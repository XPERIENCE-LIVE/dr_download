import React, { useState } from "react";
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function DownloadPanel() {
  const [url, setUrl] = useState("");
  const [format, setFormat] = useState("video");
  const [output, setOutput] = useState("");
  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState(null);

  const handleSelectFolder = async () => {
    if (window.electronAPI?.selectFolder) {
      const folder = await window.electronAPI.selectFolder();
      if (folder) {
        setOutput(folder);
      }
    }
  };

  const handleDownload = async () => {
    if (!output) {
      alert("Please choose an output folder first.");
      return;
    }
    try {
      const res = await axios.post(`${API_BASE_URL}/download/`, {
        url,
        format,
        output_dir: output
      });
      setTaskId(res.data.task_id);
    } catch (error) {
      console.error("Error starting download:", error);
    }
  };

  const checkProgress = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/progress/${taskId}`);
      setProgress(res.data.progress);
    } catch (error) {
      console.error("Error checking progress:", error);
    }
  };

  return (
    <div>
      <input
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="YouTube or playlist URL"
      />
      <select value={format} onChange={(e) => setFormat(e.target.value)}>
        <option value="video">Video</option>
        <option value="audio">Audio</option>
      </select>
      <input value={output} onChange={(e) => setOutput(e.target.value)} placeholder="Output folder" />
      <button type="button" onClick={handleSelectFolder}>Choose...</button>
      <button onClick={handleDownload} disabled={!output}>Start Download</button>
      {taskId && <button onClick={checkProgress}>Check Progress</button>}
      {progress !== null && <p>Progress: {progress.toFixed(2)}%</p>}
    </div>
  );
}
