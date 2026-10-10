const ACTIVE = new Set(["queued", "inspecting", "downloading", "postprocessing"]);

function hasActiveDownloads(downloads) {
  return downloads.some((item) => ACTIVE.has(item.status));
}

function configureAppUpdater({ app, dialog, listDownloads }) {
  const owner = process.env.DR_DOWNLOAD_UPDATE_OWNER;
  const repo = process.env.DR_DOWNLOAD_UPDATE_REPO;
  if (!app.isPackaged || !owner || !repo) return null;
  const { autoUpdater } = require("electron-updater");
  autoUpdater.setFeedURL({ provider: "github", owner, repo });
  autoUpdater.autoDownload = true;
  autoUpdater.on("update-downloaded", async () => {
    if (hasActiveDownloads(await listDownloads())) return;
    const result = await dialog.showMessageBox({
      type: "info",
      title: "Dr. Download",
      message: "Hay una actualización lista.",
      detail: "Reinicia Dr. Download para instalarla.",
      buttons: ["Reiniciar ahora", "Más tarde"],
      defaultId: 0,
      cancelId: 1
    });
    if (result.response === 0) autoUpdater.quitAndInstall(false, true);
  });
  autoUpdater.checkForUpdates().catch(() => {});
  return autoUpdater;
}

module.exports = { configureAppUpdater, hasActiveDownloads };

