"""Load OpenTD via pythonnet and connect to Thermal Desktop."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar


DEFAULT_DWG = Path(
    r"C:\Users\Hide\v2_Thermal_Desktop_Models\research_thermal_model"
    r"\research_thermal_model.dwg"
)

_GAC_MSIL = Path(r"C:\Windows\Microsoft.NET\assembly\GAC_MSIL")
_ANSYS_CRTECH = Path(r"C:\Program Files\ANSYS Inc")

# TD 2025+ uses unversioned OpenTD; older installs use OpenTDv241, OpenTDv232, ...
_VERSIONED_NAME_RE = re.compile(r"^OpenTDv(\d+)$", re.IGNORECASE)

T = TypeVar("T")


def _assembly_sort_key(stem: str) -> tuple[int, int]:
    """Prefer unversioned OpenTD, then highest OpenTDvNNN."""
    if stem.casefold() == "opentd":
        return (2, 0)
    match = _VERSIONED_NAME_RE.match(stem)
    if match:
        return (1, int(match.group(1)))
    return (0, 0)


def _candidate_dlls() -> list[Path]:
    found: list[Path] = []

    if _GAC_MSIL.is_dir():
        for child in _GAC_MSIL.iterdir():
            if not child.is_dir():
                continue
            stem = child.name
            if stem.casefold() == "opentd" or _VERSIONED_NAME_RE.match(stem):
                found.extend(child.rglob(f"{stem}.dll"))

    if _ANSYS_CRTECH.is_dir():
        for pattern in ("OpenTD.dll", "OpenTDv*.dll"):
            found.extend(_ANSYS_CRTECH.rglob(pattern))

    uniq: dict[str, Path] = {}
    for path in found:
        if path.is_file():
            uniq[str(path.resolve()).casefold()] = path.resolve()
    return list(uniq.values())


def find_opentd_dll(explicit: str | Path | None = None) -> Path:
    """Locate OpenTD.dll / OpenTDvNNN.dll (env OPENTD_DLL, explicit, GAC, installs)."""
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path.resolve()
        raise FileNotFoundError(f"OpenTD DLL not found: {path}")

    env = os.environ.get("OPENTD_DLL")
    if env:
        path = Path(env)
        if path.is_file():
            return path.resolve()
        raise FileNotFoundError(f"OPENTD_DLL is set but not a file: {path}")

    candidates = _candidate_dlls()
    if not candidates:
        raise FileNotFoundError(
            "OpenTD DLL not found. Install Thermal Desktop / OpenTD, or set "
            "OPENTD_DLL to the full path of OpenTD.dll or OpenTDv241.dll "
            r"(often under C:\Windows\Microsoft.NET\assembly\GAC_MSIL\OpenTDv241\...)."
        )

    candidates.sort(key=lambda p: _assembly_sort_key(p.stem), reverse=True)
    return candidates[0]


def load_opentd(dll_path: str | Path | None = None) -> Any:
    """
    Import the OpenTD .NET assembly and return its Python module.

    Returns the versioned module (e.g. ``OpenTDv241``) or unversioned ``OpenTD``.
    Callers should treat the returned object as the OpenTD namespace root.
    """
    try:
        import clr  # type: ignore  # pythonnet
    except ImportError as exc:
        raise ImportError(
            "pythonnet is required for OpenTD. Install with: pip install pythonnet"
        ) from exc

    dll = find_opentd_dll(dll_path)
    dll_dir = str(dll.parent)
    if dll_dir not in sys.path:
        sys.path.append(dll_dir)

    assembly_name = dll.stem  # OpenTD or OpenTDv241
    try:
        clr.AddReference(assembly_name)
    except Exception:
        clr.AddReference(str(dll))

    module = __import__(assembly_name)
    return module


def to_rooted_pathname(OpenTD: Any, path: str | Path) -> Any:
    """
    Wrap a filesystem path as OpenTD ``Utility.RootedPathname``.

    OpenTDv241+ rejects plain Python ``str`` for DwgPathname / OutputFile / etc.
    """
    text = str(Path(path).resolve())
    try:
        return OpenTD.Utility.RootedPathname(text)
    except AttributeError:
        return text


def autocad_process_running() -> bool:
    """Return True if an AutoCAD / acad process appears to be running."""
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq acad.exe", "/NH"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return False
    return "acad.exe" in out.casefold()


def call_interruptible(
    label: str,
    fn: Callable[[], T],
    *,
    poll_s: float = 0.5,
) -> T:
    """
    DEPRECATED for OpenTD API calls.

    AutoCAD/OpenTD is not safe to drive from a worker thread. Calling
    DataMapper.Update from a background thread has caused
    ``eNotOpenForWrite`` and a dead OpenTD pipe. Prefer calling OpenTD on the
    main thread. This helper remains only for non-OpenTD waits if needed.
    """
    return fn()


def connect_thermal_desktop(
    *,
    dwg_path: str | Path | None = None,
    dll_path: str | Path | None = None,
    attach_only: bool = False,
    start_new: bool = False,
) -> tuple[Any, Any]:
    """
    Connect to Thermal Desktop and return ``(td, OpenTD_module)``.

    Preferred workflow: open ``research_thermal_model.dwg`` in TD first, then
    connect with attach (default when acad.exe is already running). Opening the
    same DWG in a second AutoCAD instance often triggers
    ``eNotOpenForWrite``.

    All OpenTD calls run on the main thread (AutoCAD is not thread-safe here).
    """
    if attach_only and start_new:
        raise ValueError("Cannot combine attach_only and start_new")

    OpenTD = load_opentd(dll_path)
    ThermalDesktop = OpenTD.ThermalDesktop
    Types = OpenTD.TdConnectConfig.Types

    dwg = Path(dwg_path) if dwg_path else DEFAULT_DWG
    if not dwg.is_file():
        raise FileNotFoundError(f"TD drawing not found: {dwg}")

    td = ThermalDesktop()
    td.ConnectConfig.DwgPathname = to_rooted_pathname(OpenTD, dwg)

    if attach_only:
        td.ConnectConfig.Type = Types.ATTACH_TO_TD
        mode = "ATTACH_TO_TD"
    elif start_new:
        td.ConnectConfig.Type = Types.START_NEW_TD
        mode = "START_NEW_TD"
    elif autocad_process_running():
        # Avoid opening a second copy of the same DWG (common eNotOpenForWrite cause).
        td.ConnectConfig.Type = Types.ATTACH_TO_TD
        mode = "ATTACH_TO_TD (acad.exe detected)"
    else:
        td.ConnectConfig.Type = Types.AUTO
        mode = "AUTO"

    print(f"  OpenTD connect mode: {mode}", flush=True)
    print("  Connect() … (Ctrl+C may not interrupt native OpenTD waits)", flush=True)
    td.Connect()
    return td, OpenTD
