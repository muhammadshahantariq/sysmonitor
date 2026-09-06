#!/usr/bin/env python3
"""
sysmonitor.py - A personal system monitoring tool for YOUR OWN machines.

Features:
  info    - Show OS, hardware, and IP address details
  camera  - Check whether camera/microphone devices are currently in use
  netlog  - Log active network connections to a CSV file over time

This tool is intended to be run locally on a machine you own or
administer. It does not send data anywhere and does not run in the
background silently - every command is explicit and user-initiated.

Requirements:
    pip install psutil

Usage:
    python sysmonitor.py info
    python sysmonitor.py camera
    python sysmonitor.py netlog --interval 5 --duration 60 --output netlog.csv
"""

import argparse
import csv
import datetime
import platform
import socket
import subprocess
import sys
import time
import urllib.request

try:
    import psutil
except ImportError:
    print("This tool requires psutil. Install it with:\n    pip install psutil")
    sys.exit(1)


# ---------------------------------------------------------------------------
# System info
# ---------------------------------------------------------------------------

def get_local_ip():
    """Best-effort local IP by opening a UDP socket (no packets sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "unavailable"
    finally:
        s.close()


def get_public_ip():
    """Fetch public IP via an external service. Requires internet access."""
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:
            return resp.read().decode().strip()
    except Exception:
        return "unavailable (no internet or service blocked)"


def cmd_info(args):
    print("=" * 50)
    print("SYSTEM INFORMATION")
    print("=" * 50)

    uname = platform.uname()
    print(f"OS:            {uname.system} {uname.release} ({uname.version})")
    print(f"Machine:       {uname.machine}")
    print(f"Hostname:      {uname.node}")
    print(f"Processor:     {uname.processor or platform.processor() or 'unknown'}")

    cpu_count = psutil.cpu_count(logical=True)
    cpu_physical = psutil.cpu_count(logical=False)
    print(f"CPU cores:     {cpu_physical} physical / {cpu_count} logical")
    print(f"CPU usage:     {psutil.cpu_percent(interval=0.5)}%")

    mem = psutil.virtual_memory()
    print(f"RAM:           {mem.total / (1024**3):.2f} GB total, "
          f"{mem.percent}% used")

    disk = psutil.disk_usage("/")
    print(f"Disk (/):      {disk.total / (1024**3):.2f} GB total, "
          f"{disk.percent}% used")

    print(f"Local IP:      {get_local_ip()}")
    if not args.no_public_ip:
        print(f"Public IP:     {get_public_ip()}")

    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    print(f"Last boot:     {boot_time.strftime('%Y-%m-%d %H:%M:%S')}")


# ---------------------------------------------------------------------------
# Camera / microphone status
# ---------------------------------------------------------------------------

def check_camera_linux():
    results = []
    import glob
    video_devices = glob.glob("/dev/video*")
    if not video_devices:
        return ["No camera devices found (/dev/video*)."]

    for dev in video_devices:
        try:
            out = subprocess.run(
                ["fuser", dev], capture_output=True, text=True, timeout=3
            )
            in_use = bool(out.stdout.strip())
            status = "IN USE" if in_use else "idle"
            results.append(f"{dev}: {status}"
                            + (f" (pid(s): {out.stdout.strip()})" if in_use else ""))
        except FileNotFoundError:
            results.append(f"{dev}: found, but 'fuser' is not installed "
                            f"(try: sudo apt install psmisc)")
        except Exception as e:
            results.append(f"{dev}: could not check ({e})")
    return results


def check_camera_windows():
    """
    Reads Windows' CapabilityAccessManager consent store, which records
    which apps have recently accessed the camera/microphone.
    """
    results = []
    try:
        import winreg
    except ImportError:
        return ["winreg not available (not running on Windows?)."]

    base_paths = {
        "webcam": r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam",
        "microphone": r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone",
    }

    for label, path in base_paths.items():
        results.append(f"-- {label} --")
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path)
        except FileNotFoundError:
            results.append("  No record found.")
            continue

        idx = 0
        while True:
            try:
                app_name = winreg.EnumKey(key, idx)
            except OSError:
                break
            try:
                app_key = winreg.OpenKey(key, app_name)
                last_used_stop, _ = winreg.QueryValueEx(app_key, "LastUsedTimeStop")
                currently_active = (last_used_stop == 0)
                status = "CURRENTLY ACTIVE" if currently_active else "not active"
                results.append(f"  {app_name}: {status}")
            except Exception:
                results.append(f"  {app_name}: (could not read details)")
            idx += 1
    return results


def check_camera_macos():
    return [
        "macOS restricts direct queries into TCC.db without extra permissions.",
        "You can check current mic/camera use manually via the orange/green",
        "indicator dot in the menu bar (macOS 12+), or Control Center.",
    ]


def cmd_camera(args):
    system = platform.system()
    print("=" * 50)
    print(f"CAMERA / MIC STATUS ({system})")
    print("=" * 50)

    if system == "Linux":
        lines = check_camera_linux()
    elif system == "Windows":
        lines = check_camera_windows()
    elif system == "Darwin":
        lines = check_camera_macos()
    else:
        lines = [f"Unsupported platform: {system}"]

    for line in lines:
        print(line)


# ---------------------------------------------------------------------------
# Network connection logging
# ---------------------------------------------------------------------------

def cmd_netlog(args):
    print(f"Logging active network connections every {args.interval}s "
          f"for {args.duration}s -> {args.output}")
    print("Press Ctrl+C to stop early.\n")

    end_time = time.time() + args.duration
    fieldnames = ["timestamp", "pid", "process", "local_addr", "remote_addr", "status"]

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        try:
            while time.time() < end_time:
                timestamp = datetime.datetime.now().isoformat(timespec="seconds")
                conns = psutil.net_connections(kind="inet")
                for c in conns:
                    if not c.raddr:  # skip connections with no remote address
                        continue
                    try:
                        proc_name = psutil.Process(c.pid).name() if c.pid else "unknown"
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        proc_name = "unknown"

                    row = {
                        "timestamp": timestamp,
                        "pid": c.pid or "",
                        "process": proc_name,
                        "local_addr": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
                        "remote_addr": f"{c.raddr.ip}:{c.raddr.port}",
                        "status": c.status,
                    }
                    writer.writerow(row)
                f.flush()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped early by user.")

    print(f"Done. Log saved to {args.output}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Personal system monitoring tool for your own machines."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_info = subparsers.add_parser("info", help="Show system info (OS, hardware, IP)")
    p_info.add_argument("--no-public-ip", action="store_true",
                         help="Skip the external public-IP lookup")
    p_info.set_defaults(func=cmd_info)

    p_camera = subparsers.add_parser("camera", help="Check camera/mic access status")
    p_camera.set_defaults(func=cmd_camera)

    p_netlog = subparsers.add_parser("netlog", help="Log active network connections")
    p_netlog.add_argument("--interval", type=int, default=5,
                           help="Seconds between samples (default: 5)")
    p_netlog.add_argument("--duration", type=int, default=60,
                           help="Total seconds to log for (default: 60)")
    p_netlog.add_argument("--output", type=str, default="netlog.csv",
                           help="Output CSV file (default: netlog.csv)")
    p_netlog.set_defaults(func=cmd_netlog)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
