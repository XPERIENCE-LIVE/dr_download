# Máquina de estados

```text
queued -> inspecting -> downloading -> postprocessing -> completed
   |          |              |              |
   +----------+--------------+--------------+--> failed
   +--------------------------------------------> cancelled
```

`completed` solo se emite cuando el archivo final existe y tiene tamaño mayor que cero. `postprocessing` cubre FFmpeg y la normalización del nombre final.
