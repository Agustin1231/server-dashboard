import time
from datetime import datetime

import psutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="Server Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BOOT_TIME = psutil.boot_time()
BASE_DIR = Path(__file__).parent


def _read_temperature():
    # Try psutil first (works outside containers)
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                if key in temps and temps[key]:
                    return round(temps[key][0].current, 1)
            for entries in temps.values():
                if entries:
                    return round(entries[0].current, 1)
    except (AttributeError, OSError):
        pass

    # Fallback: read directly from sysfs (works in some Docker setups)
    import glob
    for path in sorted(glob.glob("/sys/class/thermal/thermal_zone*/temp")):
        try:
            val = int(Path(path).read_text().strip())
            return round(val / 1000.0, 1)
        except (OSError, ValueError):
            continue
    for path in sorted(glob.glob("/sys/class/hwmon/hwmon*/temp1_input")):
        try:
            val = int(Path(path).read_text().strip())
            return round(val / 1000.0, 1)
        except (OSError, ValueError):
            continue
    return None


def _format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/stats")
def stats():
    cpu_percent = psutil.cpu_percent(interval=0.3)
    cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
    load_avg = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)

    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()

    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            processes.append(
                {
                    "pid": info["pid"],
                    "name": info["name"] or "unknown",
                    "cpu": round(info["cpu_percent"] or 0.0, 1),
                    "mem": round(info["memory_percent"] or 0.0, 1),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    top_processes = sorted(processes, key=lambda p: p["cpu"], reverse=True)[:10]

    uptime_seconds = time.time() - BOOT_TIME

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cpu": {
            "percent": cpu_percent,
            "per_core": cpu_per_core,
            "count_logical": psutil.cpu_count(logical=True),
            "count_physical": psutil.cpu_count(logical=False),
            "load_avg": list(load_avg),
            "temperature_c": _read_temperature(),
        },
        "memory": {
            "total": vm.total,
            "available": vm.available,
            "used": vm.used,
            "percent": vm.percent,
        },
        "swap": {
            "total": swap.total,
            "used": swap.used,
            "percent": swap.percent,
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "mount": "/",
        },
        "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
        },
        "uptime": {
            "seconds": uptime_seconds,
            "human": _format_uptime(uptime_seconds),
            "boot_time": datetime.fromtimestamp(BOOT_TIME).isoformat(),
        },
        "top_processes": top_processes,
    }
