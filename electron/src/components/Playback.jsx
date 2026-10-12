import React, { useEffect, useRef, useState } from "react";

function clock(seconds) {
  if (!Number.isFinite(seconds)) return "—";
  const total = Math.max(0, Math.floor(seconds));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}
const streamUrl = (id, start, revision) => `dr-stream://play/${id}?start=${start}&revision=${revision}`;

export default function Playback({ api, config, t, request, ErrorNotice, errorDetails }) {
  const [url, setUrl] = useState("");
  const [items, setItems] = useState([]);
  const [index, setIndex] = useState(0);
  const [session, setSession] = useState(null);
  const [status, setStatus] = useState("ready");
  const [error, setError] = useState(null);
  const [notices, setNotices] = useState([]);
  const [offset, setOffset] = useState(0);
  const [start, setStart] = useState(0);
  const [streamRevision, setStreamRevision] = useState(0);
  const [position, setPosition] = useState(0);
  const [skipped, setSkipped] = useState(null);
  const [paused, setPaused] = useState(false);
  const [muted, setMuted] = useState(false);
  const [maxHeight, setMaxHeight] = useState(1080);
  const generation = useRef(0);
  const activeSession = useRef(null);
  const video = useRef(null);
  const pendingSeek = useRef(null);
  const suppressed = useRef(new Set());
  const current = useRef({ api, config, t });
  current.current = { api, config, t, maxHeight, paused, muted };

  const describe = (reason) => {
    if (errorDetails) return errorDetails(reason, current.current.t).message;
    const code = reason?.detail?.code || reason?.code || "stream_unavailable";
    const key = `error_${code}`;
    return current.current.t(key) === key ? current.current.t("error_stream_unavailable") : current.current.t(key);
  };
  const stop = async () => {
    const id = activeSession.current;
    activeSession.current = null;
    if (id) await current.current.api.stopPlayback(id);
  };
  const close = async () => {
    generation.current += 1;
    setSession(null); setStatus("ready"); setError(null); setSkipped(null);
    try { await stop(); } catch (reason) { setError(reason); }
  };
  const resolve = async (queue, from, step = 1, clearNotices = true) => {
    const revision = ++generation.current;
    setItems(queue); setIndex(from); setSession(null); setStatus("resolving"); setError(null); setSkipped(null);
    setPosition(0); setStart(0); setStreamRevision(0); setOffset(0); setPaused(false); suppressed.current.clear(); pendingSeek.current = null;
    if (clearNotices) setNotices([]);
    try { await stop(); }
    catch (reason) { if (revision === generation.current) { setError(reason); setStatus("playbackError"); } return; }
    for (let cursor = from; cursor >= 0 && cursor < queue.length; cursor += step) {
      if (revision !== generation.current) return;
      const item = queue[cursor];
      setIndex(cursor);
      try {
        if (item.available === false) throw { code: "item_unavailable" };
        const settings = current.current.config;
        const result = await current.current.api.startPlayback({ url: item.url, cookie_source: settings.cookie_consent === true ? settings.cookie_source : "none", max_height: current.current.maxHeight });
        if (revision !== generation.current) {
          await current.current.api.stopPlayback(result.session_id);
          return;
        }
        activeSession.current = result.session_id;
        setSession(result); setStatus("buffering"); setError(null);
        return;
      } catch (reason) {
        if (revision !== generation.current) return;
        setNotices((previous) => [...previous, `${item.title || item.url || current.current.t("itemUnavailable")}: ${describe(reason)}`]);
        setError(reason);
      }
    }
    if (revision === generation.current) setStatus("ended");
  };

  useEffect(() => {
    if (request) resolve(request.items, request.index || 0);
    // A request is an intentional new queue; configuration changes never restart playback.
  }, [request]);
  useEffect(() => () => {
    generation.current += 1;
    const id = activeSession.current;
    activeSession.current = null;
    if (id) current.current.api.stopPlayback(id).catch(() => {});
  }, []);

  const seek = (value) => {
    if (!session || !Number.isFinite(value) || value < 0 || !Number.isFinite(session.duration) || value > session.duration) return;
    const revision = ++generation.current;
    pendingSeek.current = { src: streamUrl(session.session_id, value, revision), delta: null, actualStart: null };
    setStreamRevision(revision);
    setError(null);
    setPosition(value); setOffset(value); setStart(value);
    setStatus("buffering");
  };
  const completeSeek = () => {
    const pending = pendingSeek.current;
    const element = video.current;
    if (!pending || pending.started || !element || element.getAttribute("src") !== pending.src || !Number.isFinite(pending.delta) || element.readyState < 3) return;
    const finish = () => {
      element.playbackRate = 1;
      element.muted = current.current.muted;
      pendingSeek.current = null;
      setPosition(pending.actualStart + element.currentTime);
      if (current.current.paused) {
        if (pending.started) element.pause();
        setStatus("paused");
      } else {
        setStatus("playing");
        if (!pending.started) element.play().catch(() => { setPaused(true); setStatus("paused"); });
      }
    };
    try {
      if (pending.delta === 0) { finish(); return; }
      // Streaming MP4 cannot serve byte seeks; decode the keyframe lead-in silently.
      pending.started = true;
      element.playbackRate = pending.delta > 0.5 ? 4 : 1;
      const frame = (_, metadata) => {
        if (video.current !== element || pendingSeek.current !== pending) return;
        if (metadata.mediaTime + 0.001 >= pending.delta) finish();
        else {
          if (pending.delta - metadata.mediaTime <= 0.5) element.playbackRate = 1;
          element.requestVideoFrameCallback(frame);
        }
      };
      element.requestVideoFrameCallback(frame);
      element.play().catch(() => {
        if (video.current === element && pendingSeek.current === pending) {
          setError({ code: "stream_unavailable" }); setStatus("playbackError");
        }
      });
    } catch { setError({ code: "stream_unavailable" }); setStatus("playbackError"); }
  };
  const timeUpdate = (event) => {
    if (pendingSeek.current || video.current !== event.currentTarget) return;
    const absolute = Math.max(0, offset + event.currentTarget.currentTime);
    setPosition(Number.isFinite(session.duration) ? Math.min(session.duration, absolute) : absolute);
    if (config.sponsorblock_consent !== true) return;
    session.sponsor_segments?.forEach((part) => { if (absolute >= part.end) suppressed.current.delete(part.start); });
    const segment = session.sponsor_segments?.find((part) => absolute >= part.start && absolute < part.end && !suppressed.current.has(part.start));
    if (segment) { suppressed.current.add(segment.start); setSkipped(segment); seek(segment.end); }
  };
  const loaded = async (event) => {
    if (!api.getPlayback) return;
    const revision = generation.current;
    const element = event.currentTarget;
    const source = element.getAttribute("src");
    const isCurrent = () => revision === generation.current && video.current === element && element.getAttribute("src") === source;
    const requestedStart = start;
    try {
      const result = await api.getPlayback(session.session_id);
      if (result.error) throw result.error;
      if (isCurrent() && source === streamUrl(session.session_id, requestedStart, streamRevision) && Number.isFinite(result.actual_start)) {
        setOffset(result.actual_start); setPosition(result.actual_start + video.current.currentTime);
        if (pendingSeek.current?.src === video.current.getAttribute("src")) {
          pendingSeek.current.delta = Math.max(0, requestedStart - result.actual_start);
          pendingSeek.current.actualStart = result.actual_start;
          completeSeek();
        }
      }
    } catch (reason) { if (isCurrent()) { setError(reason); setStatus("playbackError"); } }
  };
  const mediaError = async (event) => {
    const revision = generation.current;
    const element = event.currentTarget;
    const source = element.getAttribute("src");
    const isCurrent = () => revision === generation.current && video.current === element && element.getAttribute("src") === source;
    if (!isCurrent()) return;
    setStatus("playbackError");
    setError({ code: "stream_unavailable" });
    if (api.getPlayback) {
      try {
        const result = await api.getPlayback(session.session_id);
        if (isCurrent() && result.error) setError(result.error);
      } catch (reason) { if (isCurrent()) setError(reason); }
    }
    if (isCurrent()) {
      try { await stop(); } catch (reason) { if (isCurrent()) setError(reason); }
    }
  };
  const next = async () => {
    if (index + 1 < items.length) resolve(items, index + 1, 1, false);
    else {
      generation.current += 1;
      setSession(null); setStatus("ended");
      try { await stop(); } catch (reason) { setError(reason); }
    }
  };
  const ended = async (event) => {
    const element = event.currentTarget;
    const revision = generation.current;
    const isCurrent = () => revision === generation.current && video.current === element;
    try {
      // Providers can round metadata to whole seconds; backend completion remains mandatory.
      const tolerance = Number.isInteger(session.duration) ? 1 : 0.25;
      if (Number.isFinite(session.duration) && offset + element.currentTime < session.duration - tolerance) throw { code: "stream_unavailable" };
      if (api.getPlayback) {
        const result = await api.getPlayback(session.session_id);
        if (result.error) throw result.error;
        if (result.status !== "ended") throw { code: "stream_unavailable" };
      }
      if (isCurrent()) await next();
    } catch (reason) {
      if (isCurrent()) {
        setError(reason); setStatus("playbackError");
        try { await stop(); } catch (stopError) { if (isCurrent()) setError(stopError); }
      }
    }
  };
  const togglePause = () => {
    if (!video.current) return;
    if (video.current.paused) video.current.play().catch(() => { setPaused(true); setStatus("paused"); });
    else video.current.pause();
  };

  return <section className="workspace playback-workspace" aria-labelledby="player-title">
    <header className="workspace-header"><div><p className="eyebrow">YouTube · Vimeo</p><h1 id="player-title">{t("player")}</h1><p>{t("streamingHint")}</p></div><span className="status-chip" role="status">{t(status)}</span></header>
    <form className="composer panel player-composer" onSubmit={(event) => { event.preventDefault(); if (url.trim() && status !== "resolving") resolve([{ url: url.trim(), available: true }], 0); }}>
      <label htmlFor="playback-url">{t("url")}</label><div className="url-row"><input id="playback-url" type="url" required value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://youtu.be/…" /><button className="primary" disabled={!url.trim() || !api || status === "resolving"}>{t("play")}</button></div>
      <label className="playback-quality">{t("maxHeight")}<select value={maxHeight} onChange={(event) => setMaxHeight(Number(event.target.value))}><option value={1080}>1080p</option><option value={720}>720p</option><option value={480}>480p</option></select></label>
    </form>
    {session && <div className="player-stage panel"><h2>{session.title}</h2>
      <video key={`${session.session_id}:${streamRevision}`} ref={video} src={streamUrl(session.session_id, start, streamRevision)} autoPlay={!paused && start === 0} muted={muted || Boolean(pendingSeek.current)} style={{ visibility: pendingSeek.current ? "hidden" : "visible" }} playsInline aria-label={session.title}
        onLoadedMetadata={loaded} onCanPlay={completeSeek} onTimeUpdate={timeUpdate} onWaiting={(event) => { if (video.current === event.currentTarget) setStatus("buffering"); }} onPlaying={(event) => { if (video.current === event.currentTarget && !pendingSeek.current) { setStatus("playing"); setPaused(false); } }} onPause={(event) => { if (video.current === event.currentTarget && !pendingSeek.current) { setStatus("paused"); setPaused(true); } }} onEnded={ended} onError={mediaError} />
      <div className="card-actions player-controls"><button disabled={Boolean(pendingSeek.current)} onClick={togglePause}>{t(paused ? "resume" : "pause")}</button><button onClick={() => setMuted(!muted)}>{t(muted ? "unmute" : "mute")}</button><button onClick={async () => { try { if (document.fullscreenElement) await document.exitFullscreen(); else await video.current.parentElement.requestFullscreen(); } catch { setError({ code: "fullscreen_unavailable" }); } }}>{t("fullscreen")}</button></div>
      {Number.isFinite(session.duration) && session.duration > 0 ? <label className="player-timeline">{t("position")}<input aria-label={t("position")} type="range" min="0" max={session.duration} step="0.01" value={position} onChange={(event) => seek(Number(event.target.value))} /><span>{clock(position)} / {clock(session.duration)}</span></label> : <p>{t("durationUnknown")}</p>}
      <p className="estimate-hint">{session.height ? `${session.height}p · ` : ""}{t("seekKeyframeHint")}</p>
      {config.sponsorblock_consent === true && session.sponsor_status === "unavailable" && <p className="warning" role="status">{t("sponsorUnavailable")}</p>}
      {config.sponsorblock_consent === true && session.sponsor_status === "no_segments" && <p className="estimate-hint" role="status">{t("sponsorNoSegments")}</p>}
      {skipped && <div className="queue-confirmation" role="status">{t("sponsorSkipped")}<button className="secondary" onClick={() => { suppressed.current.add(skipped.start); seek(skipped.start); setSkipped(null); }}>{t("undoSkip")}</button></div>}
    </div>}
    {notices.length > 0 && <ul className="warning playback-notices" aria-label={t("skippedItems")} role="status">{notices.map((notice, number) => <li key={number}>{notice}</li>)}</ul>}
    {error && (ErrorNotice ? <ErrorNotice reason={error} t={t}><button className="secondary" onClick={() => resolve(items, index)}>{t("reload")}</button></ErrorNotice> : <div className="error-card" role="alert">{describe(error)}<button className="secondary" onClick={() => resolve(items, index)}>{t("reload")}</button></div>)}
    {items.length > 0 && <div className="card-actions"><button disabled={index <= 0} onClick={() => resolve(items, index - 1, -1)}>{t("previous")}</button><button disabled={index + 1 >= items.length} onClick={() => resolve(items, index + 1)}>{t("next")}</button><button onClick={close}>{t("closePlayer")}</button></div>}
  </section>;
}
