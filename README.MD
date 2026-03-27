# Network Performance Monitor

A desktop application for monitoring network devices using ICMP ping, TCP port checks, and comprehensive diagnostics. Built with Python and CustomTkinter for a modern, cross‑platform user interface.

## Features

- **Device Management**: Add, edit, and delete network devices (name, host/IP, optional TCP port). Settings are stored in a JSON file.
- **ICMP Ping Monitoring**: Continuous ping checks at a configurable interval, displaying latency and success/failure in real‑time.
- **TCP Port Monitoring**: Optional TCP port checks (e.g., to verify if a service is listening).
- **Network Quality Assessment**: After running a diagnostic, the app assigns a quality rating (Good / Moderate / Bad) based on ping latency and packet loss, with color‑coded rows for quick visual reference.
- **Device vs Network Diagnostic**: For any device, run a detailed test that includes:
  - 3‑packet ping with statistics
  - TCP port check (if configured)
  - Traceroute (using system command)
- **Modern UI**: Dark theme, responsive layout, and intuitive controls built with CustomTkinter.

## Installation

### Prerequisites

- Python 3.7 or higher
- `pip` (Python package manager)

### Steps

1. **Clone or download** the repository:
   ```bash
   git clone https://github.com/yourusername/network-monitor.git
   cd network-monitor
   ```

2. **Install required packages**:
   ```bash
   pip install customtkinter ping3
   ```
   > Note: On some systems, you may need to use `pip3` or `python -m pip install`.

3. **Run the application**:
   ```bash
   python network_monitor.py
   ```
   > Use `python3` if applicable.

## Usage

### Device Management (Left Panel)

**Add Device**: Click **Add Device** and fill in:

- Name (optional, shown in the list)
- Host / IP (required)
- TCP Port (optional, leave blank to skip TCP checks)

**Edit Device**: Select a device and click **Edit Device**.

**Delete Device**: Select a device and click **Delete Device**.

All devices are saved automatically in `devices.json` in the same folder.

### Monitoring (Right Panel – Top)

Set the monitoring interval (seconds) and click **Start Monitoring**.

The log will show ping results (latency or timeout) and TCP port status (if configured) for each device at each interval.

Click **Stop Monitoring** to pause.

### Diagnostics (Right Panel – Bottom)

Select a device from the dropdown.

Click **Run Diagnostic**.

The output displays:

- Ping test results (3 packets) with statistics.
- Network quality (**Good / Moderate / Bad**) based on:
  - **Good**: average ping < 50 ms, 0% loss
  - **Moderate**: average ping 50‑150 ms, loss < 10%
  - **Bad**: average ping > 150 ms or loss ≥ 10% (or all pings fail)
- TCP port check (if a port is configured).
- Traceroute output (shows the route to the target).

After the diagnostic, the device list will show the quality rating in a dedicated column, with color coding:

- 🟢 Green – Good
- 🟡 Orange – Moderate
- 🔴 Red – Bad
- ⚪ Gray – Unknown (no diagnostic run yet)

## File Structure

```text
network-monitor/
├── network_monitor.py   # Main application code
├── devices.json         # Device storage (created automatically)
└── README.md            # This file
```

## Troubleshooting

### Ping Permission Errors

On Linux/macOS, the `ping3` library may require root privileges to send ICMP packets. If you get permission errors, run the script with `sudo`:

```bash
sudo python network_monitor.py
```

Alternatively, you can modify the script to use the system `ping` command (see the code comments).

### Traceroute Not Found

The diagnostic section uses the system's `tracert` (Windows) or `traceroute` (Linux/macOS) command. If these are not installed, you may see an error. Install them via your package manager if needed.

### Save Button Not Visible

If the Add/Edit dialog appears without a Save button, the window might be too small. You can manually resize the dialog by dragging its bottom edge, or increase the height in the code (line `dialog.geometry("300x300")`).

## Customization

- **Monitoring Interval**: Change the default in `MONITOR_INTERVAL` (line ~15) or via the UI.
- **Quality Thresholds**: Modify the `evaluate_quality()` function to adjust the classification criteria.
- **Storing Quality**: By default, the quality rating is not saved to `devices.json` (it is only kept in memory while the app runs). To save it, uncomment the lines in `save_devices()` and add the quality field in `run_diagnostic()`.

## License

This project is open source and available under the MIT License.
