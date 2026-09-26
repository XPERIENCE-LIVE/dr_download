import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { translator } from "./i18n";
import "./styles/main.css";

const ACTIVE = new Set(["queued", "inspecting", "downloading", "postprocessing"]);
const defaultConfig = {
  language: "es", cookie_source: "edge", cookie_consent: false, notifications: true,
  output_dir: "", default_format: "video"
};

export function findNewCompletions(previous, current) {
  return current.filter((item) => item.status === "completed" && previous[item.id] && previous[item.id] !== "completed");
}

function formatDuration(seconds) {
  if (!Number.isFinite(seconds)) return "—";
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

function formatBytes(value) {
  if (!value) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) { size /= 1024; unit += 1; }
  return `${size.toFixed(unit > 1 ? 1 : 0)} ${units[unit]}`;
}

function Icon({ name }) {
  const paths = {
    new: "M12 5v14M5 12h14", queue: "M5 6h14M5 12h14M5 18h9", history: "M12 8v5l3 2M4 12a8 8 0 1 0 2-5.3L4 9",
    settings: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM19 12l2-1-2-3-2 .5-1-1.5.5-2L12 2 9 3l.5 2-1.5 1-2-.5-2 3 2 1v2l-2 1 2 3 2-.5 1.5 1-.5 2 3 1 3-1-.5-2 1.5-1 2 .5 2-3-2-1v-2Z",
    about: "M12 11v6M12 7h.01"
  };
  return <svg aria-hidden="true" viewBox="0 0 24 24"><path d={paths[name]} /></svg>;
}

function SignalLine({ progress = 0, status = "queued" }) {
  return (
    <div className={`signal-line signal-${status}`} aria-label={`${progress}%`}>
      <span style={{ width: `${Math.max(3, progress)}%` }} />
      <i style={{ left: `${Math.min(98, Math.max(2, progress))}%` }} />
    </div>
  );
}

function NewDownload({ api, config, setConfig, directoryCheck, setDirectoryCheck, downloads, setDownloads, t }) {
  const [url, setUrl] = useState("");
  const [media, setMedia] = useState(null);
  const [formatId, setFormatId] = useState("video-best");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [justQueued, setJustQueued] = useState(false);

  const validateDirectory = async (path = config.output_dir) => {
    if (!api?.validateDirectory) return { accepted: Boolean(path), valid: Boolean(path), path };
    const result = await api.validateDirectory({ path: path || "" });
    setDirectoryCheck(result);
    if (result.accepted && result.path && result.path !== config.output_dir) {
      setConfig((current) => ({ ...current, output_dir: result.path }));
    }
    return result;
  };

  const inspect = async () => {
    if (!url.trim()) return;
    setBusy(true); setError(""); setMedia(null); setJustQueued(false);
    try {
      const result = await api.inspectMedia({
        url: url.trim(),
        cookie_source: config.cookie_consent ? config.cookie_source : "none"
      });
      setMedia(result);
      await validateDirectory();
      const preferred = result.formats.find((item) => item.kind === config.default_format) || result.formats[0];
      if (preferred) setFormatId(preferred.id);
    } catch (reason) {
      setError(reason?.detail?.message || reason?.message || t("unknownError"));
    } finally { setBusy(false); }
  };

  const chooseFolder = async () => {
    const folder = await api.selectFolder();
    if (folder) {
      setConfig((current) => ({ ...current, output_dir: folder }));
      await validateDirectory(folder);
    }
  };

  const enqueue = async () => {
    if (!media) return;
    setBusy(true); setError("");
    try {
      const checked = await validateDirectory();
      if (!checked.accepted) {
        setError(checked.recovery || t("folderInvalid"));
        return;
      }
      const task = await api.createDownload({
        url: url.trim(), format_id: formatId, output_dir: config.output_dir,
        cookie_source: config.cookie_consent ? config.cookie_source : "none"
      });
      setDownloads((current) => [task, ...current.filter((item) => item.id !== task.id)]);
      setJustQueued(true);
    } catch (reason) {
      setError(reason?.detail?.message || reason?.message || t("unknownError"));
    } finally { setBusy(false); }
  };

  return <section className="workspace deck-workspace" aria-labelledby="new-title">
    <div className="new-deck">
      <section className="capture-deck panel">
        <header className="workspace-header"><div><p className="eyebrow">INPUT CHANNEL / 01</p><h1 id="new-title">{t("new")}</h1><p>{t("pasteHint")}</p></div><span className="status-chip"><b />{t("ready")}</span></header>
        <div className="composer">
          <label htmlFor="media-url">{t("url")}</label>
          <div className="url-row"><input id="media-url" type="url" value={url} onChange={(event) => setUrl(event.target.value)} onKeyDown={(event) => event.key === "Enter" && inspect()} placeholder="https://youtu.be/…" /><button className="primary" onClick={inspect} disabled={busy || !url.trim()}>{busy ? t("inspecting") : t("inspect")}</button></div>
          <div className="track-labels"><span>ENLACE</span><span>INSPECCIÓN</span><span>FORMATO</span><span>COLA</span></div>
          <SignalLine progress={busy ? 42 : media ? 100 : 0} status={busy ? "inspecting" : media ? "completed" : "queued"} />
        </div>
        {error && <div className="error-card" role="alert"><strong>{t("errorTitle")}</strong><span>{error}</span></div>}
        {media && <article className="media-summary">
          <div className="media-thumb">{media.thumbnail ? <img src={media.thumbnail} alt="" /> : <span>DD</span>}<div className="duration">{formatDuration(media.duration)}</div></div>
          <div className="media-info"><p className="eyebrow">SIGNAL LOCKED</p><h2>{media.title}</h2><p>{media.author}</p></div>
        </article>}
      </section>
      <aside className="output-patch panel">
        <p className="eyebrow">OUTPUT PATCH</p><h2>{config.language === "es" ? "Preparar transferencia" : "Prepare transfer"}</h2>
        {media ? <><div className="media-controls"><label>{t("format")}<select value={formatId} onChange={(event) => setFormatId(event.target.value)}>{media.formats.map((item) => <option key={item.id} value={item.id}>{item.label}{item.container ? ` · ${item.container.toUpperCase()}` : ""}</option>)}</select></label>
          <label>{t("folder")}<div className="folder-control"><input title={directoryCheck?.path || config.output_dir} value={directoryCheck?.path || config.output_dir || t("folderInvalid")} readOnly /><button className="secondary" onClick={chooseFolder}>{t("choose")}</button></div></label></div>
          {directoryCheck && !directoryCheck.accepted && <div className="error-card directory-error" role="alert"><strong>{t("folderInvalid")}</strong><span>{directoryCheck.recovery || t("folderInvalid")}</span><button className="secondary" onClick={() => validateDirectory("")}>{t("useDownloads")}</button></div>}
          {directoryCheck?.accepted && <p className="directory-ready" role="status">{t("folderReady")}</p>}
          <button className="primary queue-button" onClick={enqueue} disabled={busy || !directoryCheck?.accepted}>{t("add")}</button></> : <div className="patch-empty"><span>01</span><p>{config.language === "es" ? "Inspecciona una señal para configurar su salida." : "Inspect a signal to configure its output."}</p></div>}
      </aside>
    </div>
    {(justQueued || downloads.some((item) => item.status === "queued")) && <div className="toast" role="status">{t("queued")}</div>}
    <p className="legal-note">{t("legal")}</p>
  </section>;
}

function DownloadCard({ item, api, refresh, t }) {
  const action = async (name) => { await api[name](item.id); await refresh(); };
  return <article className="download-card panel">
    <div className="download-top"><div><span className={`state state-${item.status}`}>{t(item.status)}</span><h3>{item.title || item.filename || item.url || item.id}</h3></div><strong className="percent">{Math.round(item.progress || 0)}%</strong></div>
    <SignalLine progress={item.progress || 0} status={item.status} />
    <dl className="telemetry"><div><dt>{t("speed")}</dt><dd>{item.speed_bps ? `${formatBytes(item.speed_bps)}/s` : "—"}</dd></div><div><dt>{t("eta")}</dt><dd>{item.eta_seconds ? `${item.eta_seconds}s` : "—"}</dd></div><div><dt>{t("size")}</dt><dd>{formatBytes(item.bytes_downloaded)}</dd></div></dl>
    {item.error && <p className="inline-error">{item.error.message} {item.error.recovery}</p>}
    <div className="card-actions">
      {ACTIVE.has(item.status) && <button className="danger" onClick={() => action("cancelDownload")}>{t("cancel")}</button>}
      {["failed", "cancelled", "error"].includes(item.status) && <button onClick={() => action("retryDownload")}>{t("retry")}</button>}
      {item.filename && <button onClick={() => api.openDownload(item.id, "file")}>{t("openFile")}</button>}
      {item.output_dir && <button onClick={() => api.openDownload(item.id, "folder")}>{t("openFolder")}</button>}
      {!ACTIVE.has(item.status) && <button onClick={() => action("deleteDownload")}>{t("remove")}</button>}
    </div>
  </article>;
}

function DownloadsView({ mode, downloads, api, refresh, t }) {
  const items = downloads.filter((item) => mode === "queue" ? ACTIVE.has(item.status) : !ACTIVE.has(item.status));
  return <section className="workspace"><header className="workspace-header"><div><p className="eyebrow">{mode === "queue" ? "OUTPUT / LIVE" : "ARCHIVE / LOCAL"}</p><h1>{t(mode)}</h1><p>{items.length} · Dr. Download</p></div></header>
    <div className="download-list">{items.map((item) => <DownloadCard key={item.id} item={item} api={api} refresh={refresh} t={t} />)}{!items.length && <div className="empty panel"><span className="empty-mark">∿</span><p>{t(mode === "queue" ? "emptyQueue" : "emptyHistory")}</p></div>}</div>
  </section>;
}

function Settings({ config, setConfig, api, t }) {
  const update = (key, value) => setConfig((current) => ({ ...current, [key]: value }));
  const save = () => api.updateConfig(config);
  return <section className="workspace"><header className="workspace-header"><div><p className="eyebrow">SYSTEM / LOCAL</p><h1>{t("settings")}</h1></div></header><div className="settings-grid panel">
    <label>{t("language")}<select value={config.language} onChange={(event) => update("language", event.target.value)}><option value="es">Español</option><option value="en">English</option></select></label>
    <label>{t("browser")}<select value={config.cookie_source} onChange={(event) => update("cookie_source", event.target.value)}><option value="edge">Microsoft Edge</option><option value="firefox">Mozilla Firefox</option><option value="none">{config.language === "es" ? "Sin cookies" : "No cookies"}</option></select></label>
    <label className="toggle"><input type="checkbox" checked={config.notifications} onChange={(event) => update("notifications", event.target.checked)} /><span />{t("notifications")}</label>
    <button className="primary" onClick={save}>{t("save")}</button>
    <button onClick={() => api.exportDiagnostics()}>{t("exportDiagnostics")}</button>
  </div></section>;
}

function About({ t }) {
  return <section className="workspace"><header className="workspace-header"><div><p className="eyebrow">DR / DOWNLOAD</p><h1>{t("about")}</h1></div></header><div className="about-card panel"><div className="brand-monogram large">D<span>↓</span></div><h2>Dr. Download</h2><p>{t("aboutCopy")}</p><dl><div><dt>{t("version")}</dt><dd>2.1.0</dd></div><div><dt>Motor</dt><dd>yt-dlp</dd></div><div><dt>Datos</dt><dd>100% local</dd></div></dl><p className="legal-note">{t("legal")}</p></div></section>;
}

function TransferStrip({ item, language }) {
  if (!item) return null;
  return <footer className="transfer-strip" aria-live="polite">
    <div className="transfer-now"><strong>{language === "es" ? "TRANSFERENCIA ACTIVA" : "ACTIVE TRANSFER"}</strong><span>{item.title || item.filename || item.id}</span></div>
    <div className="transfer-progress"><SignalLine progress={item.progress || 0} status={item.status} /><div className="transfer-metrics"><span>{Math.round(item.progress || 0)}%</span><span>{item.speed_bps ? `${formatBytes(item.speed_bps)}/s` : "—"}</span><span>{item.eta_seconds ? `${item.eta_seconds}s` : "—"}</span></div></div>
    <span className="engine-state">{item.status === "postprocessing" ? (language === "es" ? "PROCESANDO" : "PROCESSING") : (language === "es" ? "DESCARGANDO" : "DOWNLOADING")}</span>
  </footer>;
}

export default function App() {
  const api = window.drDownload;
  const [view, setView] = useState("new");
  const [config, setConfig] = useState(defaultConfig);
  const [downloads, setDownloads] = useState([]);
  const [directoryCheck, setDirectoryCheck] = useState(null);
  const previousStatuses = useRef({});
  const downloadsLoaded = useRef(false);
  const t = useMemo(() => translator(config.language), [config.language]);
  const refresh = useCallback(async () => { if (api) setDownloads(await api.listDownloads()); }, [api]);

  useEffect(() => {
    if (!api) return;
    Promise.all([api.getConfig(), api.listDownloads()]).then(([saved, items]) => {
      previousStatuses.current = Object.fromEntries(items.map((item) => [item.id, item.status]));
      downloadsLoaded.current = true;
      setConfig({ ...defaultConfig, ...saved });
      setDownloads(items);
    });
  }, [api]);
  useEffect(() => {
    if (!api || !downloadsLoaded.current) return;
    const completed = findNewCompletions(previousStatuses.current, downloads);
    if (config.notifications) completed.forEach((item) => api.notify("Dr. Download", `${item.title || item.filename || t("completed")} · ${t("completed")}`));
    previousStatuses.current = Object.fromEntries(downloads.map((item) => [item.id, item.status]));
  }, [api, config.notifications, downloads, t]);
  useEffect(() => {
    if (!api || process.env.NODE_ENV === "test") return undefined;
    const timer = setInterval(refresh, 1500);
    return () => clearInterval(timer);
  }, [api, refresh]);

  const nav = ["new", "queue", "history", "settings", "about"];
  const activeTransfer = downloads.find((item) => ACTIVE.has(item.status));
  return <div className={`app-shell${activeTransfer ? " has-transfer" : ""}`}>
    <header className="deck-topbar"><div className="brand"><div className="brand-monogram">D<span>↓</span></div><div><strong>Dr. Download</strong><small>MEDIA SIGNAL</small></div></div><nav aria-label="Principal">{nav.map((name) => <button key={name} className={view === name ? "active" : ""} onClick={() => setView(name)}><Icon name={name} /><span>{t(name)}</span>{name === "queue" && downloads.filter((item) => ACTIVE.has(item.status)).length > 0 && <b>{downloads.filter((item) => ACTIVE.has(item.status)).length}</b>}</button>)}</nav><div className="engine-ready"><span className="pulse" />{config.language === "es" ? "MOTOR LOCAL LISTO" : "LOCAL ENGINE READY"}</div></header>
    <main>{view === "new" && <NewDownload api={api} config={config} setConfig={setConfig} directoryCheck={directoryCheck} setDirectoryCheck={setDirectoryCheck} downloads={downloads} setDownloads={setDownloads} t={t} />}{["queue", "history"].includes(view) && <DownloadsView mode={view} downloads={downloads} api={api} refresh={refresh} t={t} />}{view === "settings" && <Settings config={config} setConfig={setConfig} api={api} t={t} />}{view === "about" && <About t={t} />}</main>
    <TransferStrip item={activeTransfer} language={config.language} />
    {!config.cookie_consent && config.cookie_source !== "none" && <div className="consent"><div><strong>{t("consentTitle")}</strong><p>{t("consentBody")}</p></div><button className="primary" onClick={() => { const next = { ...config, cookie_consent: true }; setConfig(next); api?.updateConfig(next); }}>{t("consent")}</button></div>}
  </div>;
}
