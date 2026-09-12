"""
Hardware / environment reporting for reproducible experiment logs.

The project rubric asks every experiment to report the machine and environment
alongside its numbers. This module keeps that in one place, so each experiment
writes the same short hardware block instead of handling it ad hoc per script.

Usage:
  import sysinfo as SI
  ...
  log.extend(SI.env_lines())     # two lines for a text log
  row["runtime_s"] = ...          # wall-clock time is measured by the caller
  row.update(SI.env_dict())       # optional: same fields embeddable in a CSV

Everything is best-effort and dependency-free: on a platform where a field
cannot be read, it is simply reported as empty.
"""

import os
import platform


def _total_ram_gb():
    """Best-effort total physical RAM in GB, or None if unavailable."""
    try:
        if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:
            pages = os.sysconf("SC_PHYS_PAGES")
            size = os.sysconf("SC_PAGE_SIZE")
            return round(pages * size / (1024 ** 3), 1)
    except Exception:
        pass
    try:
        import ctypes

        class _MemoryStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        m = _MemoryStatus()
        m.dwLength = ctypes.sizeof(_MemoryStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return round(m.ullTotalPhys / (1024 ** 3), 1)
    except Exception:
        return None


def env_dict():
    """Machine / environment fields, safe to drop straight into a CSV row."""
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu": platform.processor() or platform.machine(),
        "cpu_count": os.cpu_count(),
        "ram_gb": _total_ram_gb(),
    }


def env_lines(prefix="  "):
    """Two-line hardware block for a text log."""
    e = env_dict()
    ram = f" | RAM {e['ram_gb']}GB" if e["ram_gb"] else ""
    return [
        f"{prefix}hardware: {e['cpu']} | {e['cpu_count']} logical cores{ram}",
        f"{prefix}env: python {e['python']} | {e['platform']}",
    ]
