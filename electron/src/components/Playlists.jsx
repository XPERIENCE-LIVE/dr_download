import React, { useEffect, useRef, useState } from "react";

export default function Playlists({ api, config, t, pendingItem, onPlay, ErrorNotice }) {
  const [lists, setLists] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [name, setName] = useState("");
  const [newName, setNewName] = useState("");
  const [url, setUrl] = useState(pendingItem?.url || "");
  const [importUrl, setImportUrl] = useState("");
  const [busy, setBusy] = useState("loading");
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const importRequest = useRef(null);
  const mounted = useRef(false);
  const current = useRef({ api, config });
  current.current = { api, config };
  const selected = lists.find((list) => list.id === selectedId);
  const load = async (chooseId) => {
    const result = await api.listPlaylists();
    if (!mounted.current) return;
    setLists(result);
    setSelectedId((previous) => result.find((list) => list.id === (chooseId || previous))?.id || result[0]?.id || "");
  };
  useEffect(() => {
    mounted.current = true;
    load().catch(setError).finally(() => { if (mounted.current) setBusy(""); });
    return () => {
      mounted.current = false;
      const id = importRequest.current;
      importRequest.current = null;
      if (id) current.current.api.cancelPlaylistImport(id).catch(() => {});
    };
  }, [api]);
  useEffect(() => { setName(selected?.name || ""); setConfirmDelete(false); }, [selected?.id, selected?.name]);
  useEffect(() => { if (pendingItem) setUrl(pendingItem.url); }, [pendingItem]);
  const action = async (kind, perform) => {
    if (busy) return;
    setBusy(kind); setError(null); setNotice("");
    try { await perform(); }
    catch (reason) { if (mounted.current) setError(reason); }
    finally { if (mounted.current) setBusy(""); }
  };
  const add = () => action("saving", async () => {
    const metadata = pendingItem?.url === url.trim() ? pendingItem : null;
    const result = await api.addPlaylistItem(selected.id, { url: url.trim(), ...(metadata?.title ? { title: metadata.title } : {}), ...(Number.isFinite(metadata?.duration) ? { duration: metadata.duration } : {}), ...(metadata?.thumbnail ? { thumbnail: metadata.thumbnail } : {}) });
    await load();
    setUrl(""); setNotice(result.duplicate ? "duplicateListItem" : "itemAdded");
  });
  const importList = async () => {
    if (busy || !importUrl.trim()) return;
    const requestId = crypto.randomUUID();
    importRequest.current = requestId;
    setBusy("importing"); setError(null); setNotice("");
    let completed = false;
    try {
      const result = await api.importPlaylist({ request_id: requestId, url: importUrl.trim(), cookie_source: config.cookie_consent === true ? config.cookie_source : "none" });
      if (!mounted.current || importRequest.current !== requestId) return;
      importRequest.current = null;
      completed = true;
      setBusy("loading");
      await load(result.playlist.id);
      if (mounted.current) { setNotice(`${t("importedItems")}: ${result.imported} · ${t("unavailableItems")}: ${result.unavailable}`); setImportUrl(""); }
    } catch (reason) { if (mounted.current && (completed || importRequest.current === requestId)) setError(reason); }
    finally { if (mounted.current && (completed || importRequest.current === requestId)) { importRequest.current = null; setBusy(""); } }
  };
  const cancelImport = async () => {
    const id = importRequest.current;
    if (!id || busy === "cancelling") return;
    setBusy("cancelling");
    try {
      await api.cancelPlaylistImport(id);
      if (importRequest.current === id) { importRequest.current = null; setNotice("importCancelled"); setBusy(""); }
    } catch (reason) {
      if (reason?.detail?.code === "playlist_import_completed" || reason?.code === "playlist_import_completed") {
        if (importRequest.current !== id) return;
        importRequest.current = null;
        setBusy("loading"); setError(null);
        try { await load(); if (mounted.current) { setNotice("importCompleted"); setImportUrl(""); } }
        catch (failure) { if (mounted.current) setError(failure); }
        finally { if (mounted.current) setBusy(""); }
      } else { setError(reason); if (importRequest.current === id) setBusy("importing"); }
    }
  };
  const disabled = Boolean(busy);
  return <section className="workspace" aria-labelledby="playlists-title">
    <header className="workspace-header"><div><p className="eyebrow">{t("localData")}</p><h1 id="playlists-title">{t("playlists")}</h1><p>{t("listsHint")}</p></div>{busy && <span className="status-chip" role="status">{t(busy)}</span>}</header>
    <div className="playlist-layout"><aside className="panel playlist-library">
      <label htmlFor="new-list-name">{t("newListName")}</label><div className="url-row"><input id="new-list-name" maxLength={100} value={newName} disabled={disabled} onChange={(event) => setNewName(event.target.value)} /><button className="primary" disabled={disabled || !newName.trim()} onClick={() => action("saving", async () => { const result = await api.createPlaylist({ name: newName.trim() }); await load(result.id); setNewName(""); })}>{t("createList")}</button></div>
      <label htmlFor="selected-list">{t("chooseList")}</label><select id="selected-list" disabled={disabled || !lists.length} value={selectedId} onChange={(event) => { setSelectedId(event.target.value); setNotice(""); }}>{lists.map((list) => <option key={list.id} value={list.id}>{list.name} ({list.items.length})</option>)}</select>
      {!lists.length && !busy && <p className="estimate-hint">{t("emptyLists")}</p>}
      <div className="playlist-import"><label htmlFor="playlist-url">{t("playlistUrl")}</label><div className="url-row"><input id="playlist-url" type="url" disabled={disabled} value={importUrl} onChange={(event) => setImportUrl(event.target.value)} /><button className="secondary" disabled={disabled || !importUrl.trim()} onClick={importList}>{t("importList")}</button></div><p className="estimate-hint">{t("importHint")}</p>{importRequest.current && <button className="secondary" disabled={busy === "cancelling"} onClick={cancelImport}>{t("cancelImport")}</button>}</div>
    </aside><div className="panel playlist-detail">{selected ? <>
      <h2>{selected.name}</h2><label htmlFor="rename-list">{t("listName")}</label><div className="url-row"><input id="rename-list" maxLength={100} value={name} disabled={disabled} onChange={(event) => setName(event.target.value)} /><button className="secondary" disabled={disabled || !name.trim() || name.trim() === selected.name} onClick={() => action("saving", async () => { await api.renamePlaylist(selected.id, { name: name.trim() }); await load(); setNotice("saved"); })}>{t("renameList")}</button></div>
      <div className="card-actions"><button className="primary" disabled={disabled || !selected.items.length} onClick={() => onPlay(selected.items, 0)}>{t("playList")}</button><button className="danger" disabled={disabled} onClick={() => setConfirmDelete(true)}>{t("deleteList")}</button></div>
      {confirmDelete && <div className="warning" role="alert"><p>{t("deleteListHint")}</p><div className="card-actions"><button className="danger" disabled={disabled} onClick={() => action("saving", async () => { await api.deletePlaylist(selected.id); await load(); setConfirmDelete(false); })}>{t("confirmDelete")}</button><button disabled={disabled} onClick={() => setConfirmDelete(false)}>{t("cancel")}</button></div></div>}
      <label htmlFor="list-item-url">{t("addItemUrl")}</label><div className="url-row"><input id="list-item-url" type="url" disabled={disabled} value={url} onChange={(event) => setUrl(event.target.value)} /><button className="secondary" disabled={disabled || !url.trim()} onClick={add}>{t("addToList")}</button></div>
      {url && selected.items.some((item) => item.url === url.trim()) && <p className="warning">{t("duplicateListItem")}</p>}
      {!selected.items.length && <p className="empty">{t("emptyListItems")}</p>}
      <ol className="playlist-items">{selected.items.map((item, itemIndex) => <li key={item.id}><div><strong>{item.title || item.url || t("itemUnavailable")}</strong><small>{item.available === false ? t("itemUnavailable") : item.url}</small></div><div className="card-actions"><button disabled={disabled || item.available === false} onClick={() => onPlay(selected.items, itemIndex)} aria-label={`${t("play")}: ${item.title || item.url}`}>{t("play")}</button><button disabled={disabled} aria-label={`${t("remove")}: ${item.title || item.url}`} onClick={() => action("saving", async () => { await api.removePlaylistItem(selected.id, item.id); await load(); })}>{t("remove")}</button></div></li>)}</ol>
    </> : <p className="empty">{t("chooseListHint")}</p>}</div></div>
    {error && (ErrorNotice ? <ErrorNotice reason={error} t={t} /> : <div role="alert" className="error-card">{t(`error_${error?.detail?.code || error?.code || "playlist_storage_error"}`)}</div>)}
    {notice && <p className="queue-confirmation" role="status">{t(notice)}</p>}
    {error && <button className="secondary" disabled={disabled} onClick={() => action("loading", load)}>{t("retry")}</button>}
  </section>;
}
