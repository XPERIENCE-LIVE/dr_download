import React, { useState } from "react";
import axios from "axios";

export default function DownloadPanel() {
  const [url, setUrl] = useState("");
  const [format, setFormat] = useState("video");
  const [output, setOutput] = useState("C:/Downloads");
  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState(null);

  const handleDownload = async () => {
    try {
      const res = await axios.post("http://localhost:8000/download/", {
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
      const res = await axios.get(`http://localhost:8000/progress/${taskId}`);
      setProgress(res.data.progress);
    } catch (error) {
      console.error("Error checking progress:", error);
    }
  };

  return (
    <div>
      <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="YouTube or playlist URL" />
      <select value={format} onChange={(e) => setFormat(e.target.value)}>
        <option value="video">Video</option>
        <option value="audio">Audio</option>
      </select>
      <input value={output} onChange={(e) => setOutput(e.target.value)} placeholder="Output folder" />
      <button onClick={handleDownload}>Start Download</button>
      {taskId && <button onClick={checkProgress}>Check Progress</button>}
      {progress !== null && <p>Progress: {progress.toFixed(2)}%</p>}
    </div>
  );
}
