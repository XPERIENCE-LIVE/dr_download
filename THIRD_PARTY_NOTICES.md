# Third-party notices

Dr. Download uses Electron, React, FastAPI, Uvicorn, yt-dlp and their transitive dependencies under their respective licenses. Source distributions and license texts must accompany public releases where required.

The internal Windows build includes the Gyan.dev FFmpeg full build `2024-10-02-git-358fdf3083` (GPLv3 configuration). Its license text is distributed beside the binaries. Public redistribution still requires a legal review and compliance with the source-distribution obligations of that build.

- `ffmpeg.exe` SHA-256: `CC5A6529C66D755CC3D243511A537A44CFE130ACBA1BCEA958765EDE282AB8BE`
- `ffprobe.exe` SHA-256: `124A32653958026EBC653A5B934553DD849CACDB30835800ACB6EF80882BF4D1`

The yt-dlp updater accepts only the official `yt-dlp.exe` whose SHA-256 matches the checksum published with the upstream release.

The Windows package includes Node.js `v22.14.0` as the JavaScript runtime used by yt-dlp. Node.js is open source under the MIT license and includes third-party components under their respective licenses. Public distributions must accompany this notice with the matching Node.js license bundle from the official `v22.14.0` distribution.
