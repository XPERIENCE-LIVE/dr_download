"""Safe output-directory preparation shared by the API and downloader UI."""

from dataclasses import asdict, dataclass
import os
from pathlib import Path
import shutil
import tempfile


DEFAULT_MIN_FREE_BYTES = 128 * 1024 * 1024


def default_output_directory() -> Path:
    return Path.home() / "Downloads" / "Dr. Download"


@dataclass(frozen=True)
class DirectoryCheck:
    """Result of preparing and checking a download directory."""

    path: str
    exists: bool
    created: bool
    writable: bool
    free_bytes: int | None = None
    error: str | None = None

    @property
    def valid(self) -> bool:
        return self.exists and self.writable and self.error is None

    @property
    def accepted(self) -> bool:
        return self.valid

    @property
    def error_code(self) -> str | None:
        return self.error

    @property
    def recovery(self) -> str:
        return {
            "invalid_path": "Elige una carpeta absoluta válida.",
            "not_a_directory": "Elige una carpeta, no un archivo.",
            "not_writable": "Elige otra carpeta o revisa sus permisos.",
            "disk_full": "Libera espacio y vuelve a intentarlo.",
        }.get(self.error, "")

    def as_dict(self) -> dict:
        result = asdict(self)
        result["valid"] = self.valid
        result["accepted"] = self.accepted
        result["error_code"] = self.error_code
        result["recovery"] = self.recovery
        return result


def ensure_output_directory(
    path: str | os.PathLike[str],
    *,
    min_free_bytes: int = DEFAULT_MIN_FREE_BYTES,
) -> DirectoryCheck:
    """Create *path* when needed and return a non-throwing safety check.

    The API uses this before queueing a download so a newly selected folder
    works on first use while permission, file-path and disk-full errors remain
    actionable instead of surfacing as worker failures.
    """

    if path is None or not str(path).strip():
        path = default_output_directory()
    try:
        raw = Path(path).expanduser()
        if not raw.is_absolute():
            return DirectoryCheck(str(raw), False, False, False, error="invalid_path")
        target = raw.resolve()
    except (OSError, RuntimeError, TypeError, ValueError):
        return DirectoryCheck(str(path), False, False, False, error="invalid_path")

    created = False
    try:
        if target.exists() and not target.is_dir():
            return DirectoryCheck(str(target), True, False, False, error="not_a_directory")
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created = True
        writable = os.access(target, os.W_OK)
        if not writable:
            return DirectoryCheck(str(target), True, created, False, error="not_writable")
        try:
            with tempfile.NamedTemporaryFile(dir=target, prefix=".dr-download-check-", delete=True):
                pass
        except OSError:
            return DirectoryCheck(str(target), True, created, False, error="not_writable")
        free_bytes = int(shutil.disk_usage(target).free)
        if free_bytes < max(0, int(min_free_bytes)):
            return DirectoryCheck(str(target), True, created, False, free_bytes, "disk_full")
        return DirectoryCheck(str(target), True, created, True, free_bytes)
    except PermissionError:
        return DirectoryCheck(str(target), target.exists(), created, False, error="not_writable")
    except OSError:
        return DirectoryCheck(str(target), target.exists(), created, False, error="invalid_path")
