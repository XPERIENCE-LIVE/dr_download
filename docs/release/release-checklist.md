# Checklist de release

- [ ] `tools/quality-gate.ps1 -Level pr` aprobado en el commit exacto.
- [ ] Validador SDD y ledger anti-duplicación aprobados.
- [ ] Pytest, Jest, lint y build verdes.
- [ ] Smoke real de audio y vídeo.
- [ ] FFprobe confirma duración y streams.
- [ ] yt-dlp, FFmpeg y FFprobe versionados con hashes/licencias.
- [ ] Instalador NSIS reproducible.
- [ ] Gate unsigned prueba el artefacto exacto y registra artifact-id, SHA-256 y `publishable: false`; sin exigir firma antes de SignPath.
- [ ] Aprobación humana y firma SignPath del candidato exacto; gate post-SignPath valida SHA-256 signed, timestamp, publisher SignPath Foundation y Authenticode `Valid`.
- [ ] Actualización y rollback probados.
- [ ] Windows 10/11 instalados limpiamente.
- [ ] No hay secretos en logs.
- [ ] Changelog, privacidad y terceros actualizados.
- [ ] `tools/quality-gate.ps1 -Level release` aprobado sin opciones de omisión.
- [ ] `artifacts/quality/release-artifact.json` coincide con el instalador publicado.
- [ ] GitHub Environment `production-release` aprobó el workflow bloqueante.
- [ ] Todas las historias vigentes coinciden entre épicas/fichas/matrices y están accepted con evidencia real o reducción de scope expresamente aprobada.
- [ ] US-062–US-066 y MAN-US-062–MAN-US-066 verificados en el paquete: estados/pending/fallos ES/EN, borrador, codecs FFprobe, espacio API/IPC, consentimiento revocable y archivos preservados al repetir.
- [ ] No se reutilizan conteos/smokes históricos ni pruebas aisladas como aceptación Windows; la auditoría histórica permanece intacta.

Un check pendiente bloquea publicación; ningún script ni este checklist concede excepciones. [ADN](../engineering/project-dna.md) y [publicación Windows](windows-release.md) fijan identidad única, separación de etapas y aprobación final. La existencia de los scripts no demuestra que cumplan el contrato normativo.
