SysMonitor - Personal System Monitoring Tool
=============================================

DESCRIPTION
-----------
SysMonitor is a lightweight, cross-platform command-line tool for
monitoring your own machine. It is meant for personal use, sysadmins,
or anyone who wants quick visibility into their own device without
installing a heavyweight monitoring suite.

It runs only when you invoke it directly - there is no background
service, no silent startup, and no data is ever sent anywhere except
the one optional public-IP lookup (which you can disable).

FEATURES
--------
1. info    - Displays OS, hardware (CPU/RAM/disk), local IP, and
             public IP.
2. camera  - Checks whether the camera and/or microphone are currently
             in use, and by which process (platform-dependent detail).
3. netlog  - Logs active outbound/inbound network connections
             (process, local address, remote address, status) to a
             CSV file over a chosen time window.

SUPPORTED PLATFORMS
--------------------
- Linux   (full support for all three commands)
- Windows (full support; camera check uses the Windows privacy
           consent registry)
- macOS   (info and netlog fully supported; camera check gives
           guidance only, since macOS restricts direct access to
           that data)

REQUIREMENTS
------------
- Python 3.7 or newer
- psutil (installed via requirements.txt)
- Linux only: the "psmisc" package, for the "fuser" command used by
  the camera check
      Debian/Ubuntu: sudo apt install psmisc
      Fedora:        sudo dnf install psmisc
      Arch:          sudo pacman -S psmisc

SETUP / INSTALLATION
---------------------
1. Clone the repository:
       git clone https://github.com/muhammadshahantariq/sysmonitor.git
       cd <your-repo>

2. (Recommended) Create and activate a virtual environment:
       python3 -m venv venv
       source venv/bin/activate        (Linux/macOS)
       venv\Scripts\activate           (Windows)

3. Install dependencies:
       pip install -r requirements.txt

4. (Linux only, for the camera command) Install psmisc:
       sudo apt install psmisc

5. Run the tool:
       python sysmonitor.py info
       python sysmonitor.py camera
       python sysmonitor.py netlog --interval 5 --duration 60 --output netlog.csv

USAGE EXAMPLES
--------------
Show system info without the public-IP lookup:
    python sysmonitor.py info --no-public-ip

Check camera/mic status:
    python sysmonitor.py camera

Log network connections every 2 seconds for 5 minutes:
    python sysmonitor.py netlog --interval 2 --duration 300 --output session.csv

COMMAND REFERENCE
-----------------
info
    --no-public-ip     Skip the external public IP lookup

camera
    (no options)

netlog
    --interval N       Seconds between samples (default: 5)
    --duration N       Total seconds to log for (default: 60)
    --output FILE      Output CSV file path (default: netlog.csv)

DISCLAIMER
----------
This tool is intended for monitoring devices you own or are
authorized to administer. Using it to monitor or access devices
without the owner's knowledge or consent may be illegal in your
jurisdiction. You are responsible for how you use this software.

LICENSE
-------
Released under the MIT License. See LICENSE for details.
