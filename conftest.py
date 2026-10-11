"""Pytest scratch output lives in build/pytest-tmp, whatever the invocation folder or flags."""
from pathlib import Path

import pytest


@pytest.hookimpl(tryfirst=True)  # before pytest's tmpdir plugin reads --basetemp
def pytest_configure(config):
    root = config.rootpath.resolve()
    if config.option.basetemp is None:
        config.option.basetemp = str(root / "build" / "pytest-tmp")
        return
    chosen = Path(config.option.basetemp).resolve()
    if chosen.is_relative_to(root) and not chosen.is_relative_to(root / "build"):
        raise pytest.UsageError(
            f"--basetemp {config.option.basetemp} deja carpetas sueltas en el repositorio. "
            "Omítelo (se usa build/pytest-tmp), usa build/pytest-<nombre> o una ruta fuera del repositorio."
        )
