import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { translator } from "./i18n";
import "./styles/main.css";

const ACTIVE = new Set(["queued", "inspecting", "downloading", "postprocessing"]);
const defaultConfig = {
  theme: "dark", language: "es", cookie_source: "edge", cookie_consent: false, notifications: true,
  output_dir: "", default_format: "video"
};

export function findNewCompletions(previous, current) {
  return current.filter((item) => item.status === "completed" && previous[item.id] && previous[item.id] !== "completed");
}

function formatDuration(seconds) {
  if (!Number.isFinite(seconds)) return "—";
  const total = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor(total / 60) % 60;
  return `${hours ? `${hours}:${String(minutes).padStart(2, "0")}` : Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
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

function errorDetails(reason, t) {
  const detail = reason?.detail || reason || {};
  const code = detail.code || detail.error_code || detail.error;
  const messageKey = `error_${code}`;
  const recoveryKey = `recovery_${code}`;
  const sessionError = ["age_restricted", "session_required", "browser_locked"].includes(code);
  return {
    code,
    message: t(messageKey) !== messageKey ? t(messageKey) : code ? t("error_engine_error") : detail.message || reason?.message || (typeof detail === "string" ? detail : t("unknownError")),
    recovery: sessionError ? t("sessionRecovery") : t(recoveryKey) !== recoveryKey ? t(recoveryKey) : code ? t("recovery_engine_error") : detail.recovery || t("unknownError")
  };
}

function ErrorNotice({ reason, t, children }) {
  if (!reason) return null;
  const detail = errorDetails(reason, t);
  return <div className="error-card" role="alert"><strong>{t("errorTitle")}</strong><span>{detail.message}</span><span>{detail.recovery}</span>{children}</div>;
}

function SignalLine({ progress, status = "queued", label }) {
  const measured = Number.isFinite(progress);
  const value = measured ? Math.min(100, Math.max(0, progress)) : 0;
  return (
    <div className={`signal-line signal-${status}${measured ? "" : " indeterminate"}`} role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={measured ? value : undefined}>
      <span style={measured ? { width: `${value}%` } : undefined} />
      {measured && <i style={{ left: `${Math.min(98, value)}%` }} />}
    </div>
  );
}

function NewDownload({ api, config, setConfig, directoryCheck, setDirectoryCheck, downloads, setDownloads, setView, requestedUrl, configLoaded, t }) {
  const [url, setUrl] = useState("");
  const [media, setMedia] = useState(null);
  const [formatId, setFormatId] = useState("video-best");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState(null);
  const [justQueued, setJustQueued] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const currentConfig = useRef(config);
  currentConfig.current = config;
  const inspectionRevision = useRef(0);
  useEffect(() => {
    if (!requestedUrl) return;
    inspectionRevision.current += 1;
    setUrl(requestedUrl.url); setMedia(null); setError(null); setJustQueued(false);
  }, [requestedUrl]);
  const selected = media?.formats.find((item) => item.id === formatId);
  const estimate = Number.isSafeInteger(selected?.estimated_bytes) && selected.estimated_bytes > 0 ? selected.estimated_bytes : null;
  const requiredSpace = Math.max(128 * 1024 * 1024, (estimate || 0) * 2);
  const insufficientSpace = Number.isFinite(directoryCheck?.free_bytes) && directoryCheck.free_bytes < requiredSpace;
  const duplicate = downloads.some((item) => item.url === url.trim());
  const formats = media?.formats.filter((item) => advanced || ["video-compatible", "video-best", "audio-mp3"].includes(item.id)) || [];

  const validateDirectory = async (path = config.output_dir) => {
    const result = await api.validateDirectory({ path: path || "" });
    setDirectoryCheck(result);
    if (result.accepted && result.path && result.path !== config.output_dir) {
      setConfig((current) => ({ ...current, output_dir: result.path }));
    }
    return result;
  };

  const inspect = async () => {
    if (busy || !url.trim()) return;
    const revision = ++inspectionRevision.current;
    setBusy("inspecting"); setError(null); setMedia(null); setJustQueued(false);
    try {
      const result = await api.inspectMedia({
        url: url.trim(),
        cookie_source: config.cookie_consent ? config.cookie_source : "none"
      });
      if (revision !== inspectionRevision.current) return;
      setMedia(result);
      await validateDirectory();
      const preferred = result.formats.find((item) => item.kind === config.default_format && ["video-compatible", "video-best", "audio-mp3"].includes(item.id));
      if (preferred) setFormatId(preferred.id);
    } catch (reason) {
      if (revision === inspectionRevision.current) setError(reason);
    } finally { setBusy(""); }
  };

  const chooseFolder = async () => {
    if (busy) return;
    setBusy("folder"); setError(null);
    try {
      const folder = await api.selectFolder();
      if (folder) await validateDirectory(folder);
    } catch (reason) { setError(reason); }
    finally { setBusy(""); }
  };

  const useDownloads = async () => {
    if (busy) return;
    setBusy("folder"); setError(null);
    try { await validateDirectory(""); }
    catch (reason) { setError(reason); }
    finally { setBusy(""); }
  };

  const enqueue = async () => {
    if (busy || !media) return;
    setBusy("queueing"); setError(null);
    try {
      const checked = await validateDirectory();
      if (!checked.accepted) {
        setError(checked);
        return;
      }
      if (Number.isFinite(checked.free_bytes) && checked.free_bytes < requiredSpace) {
        setError({ code: "disk_full" });
        return;
      }
      const task = await api.createDownload({
        url: url.trim(), format_id: formatId, output_dir: checked.path,
        cookie_source: currentConfig.current.cookie_consent ? currentConfig.current.cookie_source : "none",
        ...(estimate ? { estimated_bytes: estimate } : {})
      });
      setDownloads((current) => [task, ...current.filter((item) => item.id !== task.id)]);
      setJustQueued(true);
    } catch (reason) {
      setError(reason);
    } finally { setBusy(""); }
  };

  return <section className="workspace deck-workspace" aria-labelledby="new-title">
    <div className="new-deck">
      <section className="capture-deck panel">
        <header className="workspace-header"><div><p className="eyebrow">{t("input")}</p><h1 id="new-title">{t("new")}</h1><p>{t("pasteHint")}</p></div><span className="status-chip">{busy === "inspecting" ? t("inspecting") : media ? t("inspected") : t("ready")}</span></header>
        <div className="composer">
          <label htmlFor="media-url">{t("url")}</label>
          <div className="url-row"><input id="media-url" type="url" value={url} disabled={Boolean(busy) || !configLoaded} onChange={(event) => { setUrl(event.target.value); setMedia(null); setJustQueued(false); setError(null); }} onKeyDown={(event) => event.key === "Enter" && inspect()} placeholder="https://youtu.be/…" /><button className="primary" onClick={inspect} disabled={Boolean(busy) || !configLoaded || !url.trim()}>{busy === "inspecting" ? t("inspecting") : t("inspect")}</button></div>
          <div className="track-labels"><span>{t("input")}</span><span>{t("inspection")}</span><span>{t("format")}</span><span>{t("queue")}</span></div>
          {(busy === "inspecting" || busy === "queueing") && <SignalLine status={busy} label={t(busy)} />}
          {duplicate && <p className="warning" role="status">{t("duplicate")}</p>}
        </div>
        <ErrorNotice reason={error} t={t}><div className="card-actions"><button className="secondary" disabled={Boolean(busy)} onClick={inspect}>{t("reinspect")}</button><button className="secondary" onClick={() => setView("settings")}>{t("settings")}</button></div></ErrorNotice>
        {media && <article className="media-summary">
          <div className="media-thumb">{media.thumbnail ? <img src={media.thumbnail} alt="" /> : <span>DD</span>}<div className="duration">{formatDuration(media.duration)}</div></div>
          <div className="media-info"><p className="eyebrow">{t("inspected")}</p><h2>{media.title}</h2><p>{media.author}</p></div>
        </article>}
      </section>
      <aside className="output-patch panel">
        <p className="eyebrow">{t("output")}</p><h2>{t("prepare")}</h2>
        {media ? <><div className="media-controls"><label>{t("format")}<select value={formatId} disabled={Boolean(busy)} onChange={(event) => setFormatId(event.target.value)}>{formats.map((item) => <option key={item.id} value={item.id}>{t(item.id) !== item.id ? t(item.id) : item.label}{item.container ? ` · ${item.container.toUpperCase()}` : ""}</option>)}</select></label>
          <label className="advanced-control"><input type="checkbox" checked={advanced} disabled={Boolean(busy)} onChange={(event) => { setAdvanced(event.target.checked); if (!event.target.checked && !["video-compatible", "video-best", "audio-mp3"].includes(formatId)) setFormatId(media.formats.find((item) => ["video-compatible", "video-best", "audio-mp3"].includes(item.id) && item.kind === selected?.kind)?.id || "video-best"); }} />{t("advanced")}</label>
          <p className="size-estimate">{estimate ? `${t("estimatedSize")}: ${formatBytes(estimate)}` : t("unknownSize")}</p>
          {estimate && <p className="estimate-hint">{t("estimateHint")}</p>}
            {formatId === "video-best" && <p className="estimate-hint">{t("qualityHint")}</p>}
          {Number.isFinite(directoryCheck?.free_bytes) && <p className="size-estimate">{t("freeSpace")}: {formatBytes(directoryCheck.free_bytes)}</p>}
          <label>{t("folder")}<div className="folder-control"><input title={directoryCheck?.path || config.output_dir} value={directoryCheck?.path || config.output_dir || t("folderInvalid")} readOnly /><button className="secondary" disabled={Boolean(busy)} onClick={chooseFolder}>{t("choose")}</button></div></label></div>
          {directoryCheck && (!directoryCheck.accepted || insufficientSpace) && <div className="error-card directory-error" role="alert"><strong>{insufficientSpace ? t("insufficientSpace") : t("folderInvalid")}</strong><span>{insufficientSpace ? t("recovery_disk_full") : errorDetails(directoryCheck, t).recovery}</span><button className="secondary" disabled={Boolean(busy)} onClick={useDownloads}>{t("useDownloads")}</button></div>}
          {directoryCheck?.accepted && <p className="directory-ready" role="status">{t("folderReady")}</p>}
          <button className="primary queue-button" onClick={enqueue} disabled={Boolean(busy) || !directoryCheck?.accepted || insufficientSpace || !selected}>{busy === "queueing" ? t("queueing") : t("add")}</button></> : <div className="patch-empty"><span aria-hidden="true">01</span><p>{t("inspectFirst")}</p></div>}
      </aside>
    </div>
    {justQueued && <div className="queue-confirmation" role="status">{t("queued")} <button className="secondary" onClick={() => setView("queue")}>{t("viewQueue")}</button></div>}
    <p className="legal-note">{t("legal")}</p>
  </section>;
}

function DownloadCard({ item, api, refresh, setView, inspectAgain, t }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const action = async (name, ...args) => {
    if (busy) return;
    setBusy(true); setError(null);
    try {
      await api[name](...args);
      if (["cancelDownload", "retryDownload", "deleteDownload"].includes(name)) await refresh();
    } catch (reason) { setError(reason); }
    finally { setBusy(false); }
  };
  const taskError = item.error && errorDetails(item.error, t);
  return <article className="download-card panel">
    <div className="download-top"><div><span className={`state state-${item.status}`}>{t(item.status)}</span><h3>{item.title || item.filename || item.url || item.id}</h3></div>{["downloading", "completed"].includes(item.status) && <strong className="percent">{Math.round(item.progress || 0)}%</strong>}</div>
    <SignalLine progress={["inspecting", "postprocessing"].includes(item.status) ? undefined : item.progress || 0} status={item.status} label={t(item.status)} />
    <dl className="telemetry"><div><dt>{t("speed")}</dt><dd>{item.speed_bps ? `${formatBytes(item.speed_bps)}/s` : "—"}</dd></div><div><dt>{t("eta")}</dt><dd>{Number.isFinite(item.eta_seconds) ? formatDuration(item.eta_seconds) : "—"}</dd></div><div><dt>{t("size")}</dt><dd>{formatBytes(item.bytes_downloaded)}</dd></div></dl>
    {taskError && <p className="inline-error">{taskError.message} {taskError.recovery}</p>}
    <ErrorNotice reason={error} t={t} />
    <div className="card-actions">
      {ACTIVE.has(item.status) && <button disabled={busy} className="danger" onClick={() => action("cancelDownload", item.id)}>{t("cancel")}</button>}
      {["failed", "cancelled", "error"].includes(item.status) && <button disabled={busy} onClick={() => action("retryDownload", item.id)}>{t("retry")}</button>}
      {item.error?.code === "format_unavailable" && <button onClick={() => inspectAgain(item.url)}>{t("reinspect")}</button>}
      {taskError && <button onClick={() => setView("settings")}>{t("settings")}</button>}
      {item.filename && <button disabled={busy} onClick={() => action("openDownload", item.id, "file")}>{t("openFile")}</button>}
      {item.output_dir && <button disabled={busy} onClick={() => action("openDownload", item.id, "folder")}>{t("openFolder")}</button>}
      {!ACTIVE.has(item.status) && <button disabled={busy} onClick={() => action("deleteDownload", item.id)}>{t("remove")}</button>}
    </div>
  </article>;
}

function DownloadsView({ mode, downloads, api, refresh, setView, inspectAgain, t }) {
  const [search, setSearch] = useState("");
  const [state, setState] = useState("all");
  const items = downloads.filter((item) => mode === "queue" ? ACTIVE.has(item.status) : !ACTIVE.has(item.status)
    && (state === "all" || item.status === state)
    && [item.title, item.url, item.filename].some((value) => (value || "").toLocaleLowerCase().includes(search.trim().toLocaleLowerCase())));
  return <section className="workspace"><header className="workspace-header"><div><p className="eyebrow">{t(mode === "queue" ? "queue" : "localData")}</p><h1>{t(mode)}</h1><p>{items.length} · Dr. Download</p></div></header>
    {mode === "history" && <div className="history-controls"><label>{t("searchHistory")}<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label>{t("state")}<select value={state} onChange={(event) => setState(event.target.value)}>{["all", "completed", "failed", "cancelled"].map((value) => <option key={value} value={value}>{t(value === "all" ? "allStates" : value)}</option>)}</select></label></div>}
    <div className="download-list">{items.map((item) => <DownloadCard key={item.id} item={item} api={api} refresh={refresh} setView={setView} inspectAgain={inspectAgain} t={t} />)}{!items.length && <div className="empty panel"><span className="empty-mark" aria-hidden="true">∿</span><p>{t(mode === "queue" ? "emptyQueue" : search || state !== "all" ? "noMatches" : "emptyHistory")}</p></div>}</div>
  </section>;
}

function Settings({ config, setConfig, api, externalBusy, onBusyChange, t }) {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState("");
  const disabled = Boolean(busy) || externalBusy;
  const update = (key, value) => {
    setSuccess("");
    setConfig((current) => ({ ...current, [key]: value,
      ...(key === "cookie_source" && value !== current.cookie_source ? { cookie_consent: false } : {}) }));
  };
  const save = async (revoke = false) => {
    if (disabled) return;
    onBusyChange(true);
    setBusy("saving"); setError(null); setSuccess("");
    const next = revoke ? { ...config, cookie_consent: false } : config;
    // Revocation stops reads immediately even if saving the preference fails.
    if (revoke) setConfig(next);
    try { await api.updateConfig(next); setSuccess(revoke ? "consentRevoked" : "saved"); }
    catch (reason) { setError(reason); }
    finally { setBusy(""); onBusyChange(false); }
  };
  const exportDiagnostics = async () => {
    if (disabled) return;
    setBusy("exporting"); setError(null); setSuccess("");
    try { if (await api.exportDiagnostics()) setSuccess("exported"); }
    catch (reason) { setError(reason); }
    finally { setBusy(""); }
  };
  return <section className="workspace"><header className="workspace-header"><div><p className="eyebrow">{t("localData")}</p><h1>{t("settings")}</h1></div></header><div className="settings-grid panel">
    <label>{t("language")}<select disabled={disabled} value={config.language} onChange={(event) => update("language", event.target.value)}><option value="es">Español</option><option value="en">English</option></select></label>
    <label>{t("browser")}<select disabled={disabled} value={config.cookie_source} onChange={(event) => update("cookie_source", event.target.value)}><option value="edge">Microsoft Edge</option><option value="firefox">Mozilla Firefox</option><option value="none">{t("noCookies")}</option></select></label>
    <label className="toggle"><input disabled={disabled} type="checkbox" checked={config.notifications} onChange={(event) => update("notifications", event.target.checked)} /><span />{t("notifications")}</label>
    <button disabled={disabled} className="primary" onClick={() => save()}>{t(busy === "saving" ? "saving" : "save")}</button>
    <button disabled={disabled} onClick={exportDiagnostics}>{t(busy === "exporting" ? "exporting" : "exportDiagnostics")}</button>
    {config.cookie_consent && <button disabled={disabled} onClick={() => save(true)}>{t("revokeConsent")}</button>}
  </div><ErrorNotice reason={error} t={t} />{success && <p role="status">{t(success)}</p>}</section>;
}

function About({ t }) {
  return <section className="workspace"><header className="workspace-header"><div><p className="eyebrow">Dr. Download</p><h1>{t("about")}</h1></div></header><div className="about-card panel"><div className="brand-monogram large">D<span>↓</span></div><h2>Dr. Download</h2><p>{t("aboutCopy")}</p><dl><div><dt>{t("version")}</dt><dd>2.1.0</dd></div><div><dt>{t("engine")}</dt><dd>yt-dlp</dd></div><div><dt>{t("data")}</dt><dd>{t("localOnly")}</dd></div></dl><p className="legal-note">{t("legal")}</p></div></section>;
}

function TransferStrip({ item, t }) {
  if (!item) return null;
  return <footer className="transfer-strip" aria-live="polite">
    <div className="transfer-now"><strong>{t(item.status === "queued" ? "transferWaiting" : "transferActive")}</strong><span>{item.title || item.filename || item.id}</span></div>
    <div className="transfer-progress"><SignalLine progress={["inspecting", "postprocessing"].includes(item.status) ? undefined : item.progress || 0} status={item.status} label={t(item.status)} /><div className="transfer-metrics"><span>{item.status === "downloading" ? `${Math.round(item.progress || 0)}%` : t(item.status)}</span><span>{item.speed_bps ? `${formatBytes(item.speed_bps)}/s` : "—"}</span><span>{Number.isFinite(item.eta_seconds) ? formatDuration(item.eta_seconds) : "—"}</span></div></div>
    <span className="engine-state">{t(item.status)}</span>
  </footer>;
}

export default function App() {
  const api = window.drDownload;
  const [view, setView] = useState("new");
  const [config, setConfig] = useState(defaultConfig);
  const [downloads, setDownloads] = useState([]);
  const [directoryCheck, setDirectoryCheck] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [configError, setConfigError] = useState("");
  const [configLoaded, setConfigLoaded] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [consentBusy, setConsentBusy] = useState(false);
  const [consentError, setConsentError] = useState(null);
  const [settingsBusy, setSettingsBusy] = useState(false);
  const [requestedUrl, setRequestedUrl] = useState(null);
  const previousStatuses = useRef({});
  const downloadsLoaded = useRef(false);
  const mounted = useRef(false);
  const inFlight = useRef(null);
  const downloadsRevision = useRef(0);
  const downloadsSnapshot = useRef("[]");
  const lastLoadError = useRef("");
  const t = useMemo(() => translator(config.language), [config.language]);
  const refresh = useCallback(() => {
    if (!api) return Promise.resolve([]);
    if (inFlight.current) return inFlight.current;
    const revision = downloadsRevision.current;
    inFlight.current = api.listDownloads().then((items) => {
      if (mounted.current) {
        if (!downloadsLoaded.current) {
          setHistoryLoaded(true);
          previousStatuses.current = { ...Object.fromEntries(items.map((item) => [item.id, item.status])), ...previousStatuses.current };
          downloadsLoaded.current = true;
        }
        if (revision === downloadsRevision.current) {
          const snapshot = JSON.stringify(items);
          if (snapshot !== downloadsSnapshot.current) {
            downloadsSnapshot.current = snapshot;
            setDownloads(items);
          }
        }
        if (lastLoadError.current) {
          lastLoadError.current = "";
          setLoadError("");
        }
      }
      return items;
    }).catch((reason) => {
      if (mounted.current) {
        const message = reason?.detail?.message || reason?.message || t("unknownError");
        if (message !== lastLoadError.current) {
          lastLoadError.current = message;
          setLoadError(reason);
        }
      }
      throw reason;
    }).finally(() => { inFlight.current = null; });
    return inFlight.current;
  }, [api, t]);
  const updateDownloads = useCallback((update) => {
    downloadsRevision.current += 1;
    downloadsSnapshot.current = null;
    setDownloads(update);
  }, []);
  const refreshAfterAction = useCallback(async () => {
    if (inFlight.current) await inFlight.current.catch(() => {});
    return refresh();
  }, [refresh]);
  const activeDownloads = useMemo(() => downloads.filter((item) => ACTIVE.has(item.status)), [downloads]);
  const hasActiveDownloads = activeDownloads.length > 0;
  const loadConfiguration = useCallback(async () => {
    try {
      const saved = await api.getConfig();
      if (mounted.current) { setConfig({ ...defaultConfig, ...saved }); setConfigLoaded(true); setConfigError(""); }
    } catch (reason) { if (mounted.current) setConfigError(reason); }
  }, [api]);

  useEffect(() => {
    if (!api) return;
    mounted.current = true;
    loadConfiguration();
    refresh().catch(() => {}); // refresh exposes failures in the interface.
    return () => { mounted.current = false; };
    // Configuration is loaded once for each bridge, independently of language changes.
  }, [api]);
  useEffect(() => {
    if (!api) return;
    if (!downloadsLoaded.current) {
      previousStatuses.current = Object.fromEntries(downloads.map((item) => [item.id, item.status]));
      return;
    }
    const completed = findNewCompletions(previousStatuses.current, downloads);
    if (config.notifications) completed.forEach((item) => api.notify("Dr. Download", `${item.title || item.filename || t("completed")} · ${t("completed")}`));
    previousStatuses.current = Object.fromEntries(downloads.map((item) => [item.id, item.status]));
  }, [api, config.notifications, downloads, t]);
  useEffect(() => {
    if (!api) return undefined;
    let stopped = false;
    let polling = false;
    let timer;
    const schedule = () => {
      const delay = document.hidden ? (hasActiveDownloads ? 5000 : 30000) : (hasActiveDownloads ? 1500 : 10000);
      timer = setTimeout(poll, delay);
    };
    const poll = async () => {
      clearTimeout(timer);
      if (polling || stopped) return;
      polling = true;
      try { await refresh(); }
      catch { /* refresh exposes the error and the next scheduled read retries. */ }
      finally { polling = false; if (!stopped) schedule(); }
    };
    const onVisibilityChange = () => {
      clearTimeout(timer);
      if (!document.hidden) poll();
      else if (!polling) schedule();
    };
    schedule();
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => { stopped = true; clearTimeout(timer); document.removeEventListener("visibilitychange", onVisibilityChange); };
  }, [api, refresh, hasActiveDownloads]);

  const nav = ["new", "queue", "history", "settings", "about"];
  const activeTransfer = activeDownloads.find((item) => item.status !== "queued") || activeDownloads[0];
  const appError = configError || loadError;
  const connection = !api || appError ? "engineUnavailable" : configLoaded && historyLoaded ? "engineReady" : "connecting";
  const inspectAgain = (url) => { setRequestedUrl({ url: url || "" }); setView("new"); };
  const allowCookies = async () => {
    if (consentBusy || settingsBusy) return;
    setConsentBusy(true); setConsentError(null);
    const next = { ...config, cookie_consent: true };
    try {
      await api.updateConfig(next);
      setConfig((current) => ({ ...current, cookie_consent: current.cookie_source === next.cookie_source }));
    } catch (reason) { setConsentError(reason); }
    finally { setConsentBusy(false); }
  };
  return <div className={`app-shell${activeTransfer ? " has-transfer" : ""}`}>
    <header className="deck-topbar"><div className="brand"><div className="brand-monogram">D<span>↓</span></div><div><strong>Dr. Download</strong><small>{t("mediaTool")}</small></div></div><nav aria-label={t("navigation")}>{nav.map((name) => <button key={name} className={view === name ? "active" : ""} onClick={() => setView(name)}><Icon name={name} /><span>{t(name)}</span>{name === "queue" && hasActiveDownloads && <b>{activeDownloads.length}</b>}</button>)}</nav><div className={`engine-ready engine-${connection}`} role="status"><span className="pulse" />{t(connection)}</div></header>
    <main><ErrorNotice reason={appError} t={t}><button className="secondary" onClick={() => { if (configError) loadConfiguration(); refresh().catch(() => { /* refresh displays the failure. */ }); }}>{t("retry")}</button></ErrorNotice>
      <div hidden={view !== "new"}><NewDownload api={api} config={config} setConfig={setConfig} directoryCheck={directoryCheck} setDirectoryCheck={setDirectoryCheck} downloads={downloads} setDownloads={updateDownloads} setView={setView} requestedUrl={requestedUrl} configLoaded={configLoaded} t={t} /></div>
      {["queue", "history"].includes(view) && <DownloadsView mode={view} downloads={downloads} api={api} refresh={refreshAfterAction} setView={setView} inspectAgain={inspectAgain} t={t} />}
      <div hidden={view !== "settings"}><Settings config={config} setConfig={setConfig} api={api} externalBusy={consentBusy || !configLoaded} onBusyChange={setSettingsBusy} t={t} /></div>{view === "about" && <About t={t} />}</main>
    <TransferStrip item={activeTransfer} t={t} />
    {configLoaded && !config.cookie_consent && config.cookie_source !== "none" && <div className="consent"><div><strong>{t("consentTitle")}</strong><p>{t("consentBody")}</p><ErrorNotice reason={consentError} t={t} /></div><button disabled={consentBusy || settingsBusy} className="primary" onClick={allowCookies}>{t(consentBusy ? "consentSaving" : "consent")}</button></div>}
  </div>;
}
