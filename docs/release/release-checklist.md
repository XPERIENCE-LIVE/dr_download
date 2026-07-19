# Checklist de release

- [ ] `tools/quality-gate.ps1 -Level pr` aprobado en el commit exacto.
- [ ] Validador SDD y ledger anti-duplicación aprobados.
- [ ] Pytest, Jest, lint y build verdes.
- [ ] Smoke real de audio y vídeo.
- [ ] FFprobe confirma duración y streams.
- [ ] yt-dlp, FFmpeg y FFprobe versionados con hashes/licencias.
- [ ] Instalador NSIS reproducible.
- [ ] Firma Authenticode verificada.
- [ ] Actualización y rollback probados.
- [ ] Windows 10/11 instalados limpiamente.
- [ ] No hay secretos en logs.
- [ ] Changelog, privacidad y terceros actualizados.
- [ ] `tools/quality-gate.ps1 -Level release` aprobado sin opciones de omisión.
- [ ] `artifacts/quality/release-artifact.json` coincide con el instalador publicado.
- [ ] GitHub Environment `production-release` aprobó el workflow bloqueante.
