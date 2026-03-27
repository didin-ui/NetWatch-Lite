import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk
import json
import os
import threading
import time
import socket
import subprocess
import platform
from ping3 import ping
from datetime import datetime

# ======================== Configuration ========================
DATA_FILE = "devices.json"
MONITOR_INTERVAL = 5  # seconds between monitoring cycles

# ======================== Helper Functions ========================
def load_devices():
    """Load device list from JSON file."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_devices(devices):
    """Save device list to JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(devices, f, indent=4)

def ping_host(host, timeout=2):
    """Return (response_time_ms, success) or (None, False) on failure."""
    try:
        rtt = ping(host, timeout=timeout)
        # Treat None or zero/negative values as failure
        if rtt is None or rtt <= 0.0:
            return None, False
        return rtt * 1000, True  # convert to ms
    except Exception:
        return None, False

def tcp_check(host, port, timeout=2):
    """Return (True, "open") or (False, "closed/timeout") with optional message."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return True, "open"
        else:
            return False, "closed"
    except Exception as e:
        return False, str(e)

def traceroute(host):
    """Run traceroute/tracert and return output as string."""
    system = platform.system().lower()
    try:
        if system == "windows":
            cmd = ["tracert", "-h", "15", host]
        else:
            cmd = ["traceroute", "-m", "15", host]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return proc.stdout + proc.stderr
    except Exception as e:
        return f"Error running traceroute: {e}"

def evaluate_quality(rtt_list, loss_count, total_packets=3):
    """
    Evaluate network quality based on ping results.
    rtt_list: list of successful RTTs in ms
    loss_count: number of lost packets
    Returns: (quality_string, color_tag)
    """
    loss_pct = (loss_count / total_packets) * 100
    if not rtt_list:
        return "Bad", "bad"

    avg_rtt = sum(rtt_list) / len(rtt_list)

    if avg_rtt < 50 and loss_pct == 0:
        return "Good", "good"
    elif avg_rtt <= 150 and loss_pct < 10:
        return "Moderate", "moderate"
    else:
        return "Bad", "bad"

# ======================== Main Application ========================
class NetworkMonitorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Network Performance Monitor")
        self.geometry("1050x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Data
        self.devices = load_devices()
        self.monitoring = False
        self.monitor_thread = None

        # UI elements
        self.create_widgets()
        self.setup_treeview_tags()

        # Load devices into treeview
        self.refresh_device_list()

    def setup_treeview_tags(self):
        """Define tags for row coloring."""
        self.device_tree.tag_configure("good", foreground="green")
        self.device_tree.tag_configure("moderate", foreground="orange")
        self.device_tree.tag_configure("bad", foreground="red")
        self.device_tree.tag_configure("unknown", foreground="gray")

    def create_widgets(self):
        # Main container: two columns (left: device mgmt, right: monitoring)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ================== Left Frame (Device Management) ==================
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        left_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_frame, text="Devices", font=("Arial", 18, "bold")).pack(pady=5)

        # Treeview for devices (needs to be styled)
        tree_frame = ctk.CTkFrame(left_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.device_tree = ttk.Treeview(tree_frame, columns=("host", "port", "quality"), show="headings", height=12)
        self.device_tree.heading("host", text="Hostname/IP")
        self.device_tree.heading("port", text="Port (TCP)")
        self.device_tree.heading("quality", text="Quality")
        self.device_tree.column("host", width=150)
        self.device_tree.column("port", width=80)
        self.device_tree.column("quality", width=80)
        self.device_tree.pack(fill="both", expand=True)

        # Buttons for device management
        btn_frame = ctk.CTkFrame(left_frame)
        btn_frame.pack(pady=10, fill="x", padx=10)
        ctk.CTkButton(btn_frame, text="Add Device", command=self.add_device).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Edit Device", command=self.edit_device).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Delete Device", command=self.delete_device).pack(side="left", padx=5)

        # ================== Right Frame (Monitoring & Diagnostic) ==================
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)

        # Monitoring Controls
        mon_frame = ctk.CTkFrame(right_frame)
        mon_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(mon_frame, text="Monitoring", font=("Arial", 16, "bold")).pack(side="left", padx=10)
        self.monitor_btn = ctk.CTkButton(mon_frame, text="Start Monitoring", command=self.toggle_monitoring)
        self.monitor_btn.pack(side="left", padx=10)
        ctk.CTkLabel(mon_frame, text="Interval (s):").pack(side="left", padx=5)
        self.interval_var = ctk.IntVar(value=MONITOR_INTERVAL)
        self.interval_entry = ctk.CTkEntry(mon_frame, width=50, textvariable=self.interval_var)
        self.interval_entry.pack(side="left", padx=5)

        # Monitoring Results (scrollable text)
        mon_results = ctk.CTkFrame(right_frame)
        mon_results.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(mon_results, text="Monitoring Log", font=("Arial", 12, "bold")).pack(anchor="w", padx=5)
        self.mon_log = ctk.CTkTextbox(mon_results, wrap="word")
        self.mon_log.pack(fill="both", expand=True, padx=5, pady=5)

        # Diagnostic Section
        diag_frame = ctk.CTkFrame(right_frame)
        diag_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(diag_frame, text="Device vs Network Diagnostic", font=("Arial", 16, "bold")).pack(anchor="w", padx=5)
        diag_sel_frame = ctk.CTkFrame(diag_frame)
        diag_sel_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(diag_sel_frame, text="Select Device:").pack(side="left", padx=5)
        self.diag_device_var = ctk.StringVar()
        self.diag_device_menu = ctk.CTkOptionMenu(diag_sel_frame, variable=self.diag_device_var, values=[])
        self.diag_device_menu.pack(side="left", padx=5)
        ctk.CTkButton(diag_sel_frame, text="Run Diagnostic", command=self.run_diagnostic).pack(side="left", padx=10)

        self.diag_output = ctk.CTkTextbox(diag_frame, height=120, wrap="word")
        self.diag_output.pack(fill="x", padx=5, pady=5)

    # ================== Device Management ==================
    def refresh_device_list(self):
        """Update the device treeview and diagnostic dropdown."""
        # Clear tree
        for row in self.device_tree.get_children():
            self.device_tree.delete(row)
        # Re-populate
        for dev in self.devices:
            host = dev.get("host", "")
            port = dev.get("port", "")
            name = dev.get("name", host)
            quality = dev.get("quality", "Unknown")
            # Determine tag based on quality
            tag = "unknown"
            if quality == "Good":
                tag = "good"
            elif quality == "Moderate":
                tag = "moderate"
            elif quality == "Bad":
                tag = "bad"

            self.device_tree.insert("", "end", values=(f"{name} ({host})", port, quality), tags=(tag,))
        # Update diagnostic dropdown
        dev_names = [f"{dev.get('name', dev.get('host'))} ({dev.get('host')})" for dev in self.devices]
        self.diag_device_menu.configure(values=dev_names)
        if dev_names:
            self.diag_device_var.set(dev_names[0])

    def get_selected_device(self):
        """Return the device dict and index for the selected tree item."""
        selected = self.device_tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select a device first.")
            return None, None
        index = self.device_tree.index(selected[0])
        if 0 <= index < len(self.devices):
            return self.devices[index], index
        return None, None

    def add_device(self):
        """Dialog to add a new device."""
        self.device_dialog("Add Device", None)

    def edit_device(self):
        """Dialog to edit the selected device."""
        dev, idx = self.get_selected_device()
        if dev:
            self.device_dialog("Edit Device", dev, idx)

    def delete_device(self):
        """Delete selected device."""
        dev, idx = self.get_selected_device()
        if dev:
            if messagebox.askyesno("Confirm", f"Delete device '{dev.get('name')}'?"):
                self.devices.pop(idx)
                save_devices(self.devices)
                self.refresh_device_list()
                self.log_message(f"Deleted device: {dev.get('name')} ({dev.get('host')})")

    def device_dialog(self, title, device, index=None):
        """Generic add/edit dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("300x300")
        dialog.resizable(False, False)
        dialog.grab_set()

        # Fields
        name = ctk.StringVar(value=device.get("name", "") if device else "")
        host = ctk.StringVar(value=device.get("host", "") if device else "")
        port = ctk.StringVar(value=str(device.get("port", "")) if device else "")

        ctk.CTkLabel(dialog, text="Name (optional):").pack(pady=5)
        ctk.CTkEntry(dialog, textvariable=name).pack(pady=5)
        ctk.CTkLabel(dialog, text="Host / IP *:").pack(pady=5)
        ctk.CTkEntry(dialog, textvariable=host).pack(pady=5)
        ctk.CTkLabel(dialog, text="TCP Port (optional):").pack(pady=5)
        ctk.CTkEntry(dialog, textvariable=port).pack(pady=5)

        def save():
            host_val = host.get().strip()
            if not host_val:
                messagebox.showerror("Error", "Host/IP is required.")
                return
            port_val = None
            if port.get().strip():
                try:
                    port_val = int(port.get().strip())
                    if not (1 <= port_val <= 65535):
                        raise ValueError
                except:
                    messagebox.showerror("Error", "Invalid port number (1-65535).")
                    return
            new_dev = {
                "name": name.get().strip() or host_val,
                "host": host_val,
                "port": port_val
            }
            # Remove any previous quality (will be re-evaluated later)
            if "quality" in new_dev:
                del new_dev["quality"]

            if device is not None and index is not None:
                # Editing existing
                self.devices[index] = new_dev
            else:
                self.devices.append(new_dev)
            save_devices(self.devices)
            self.refresh_device_list()
            dialog.destroy()

        ctk.CTkButton(dialog, text="Save", command=save).pack(pady=15)

    # ================== Monitoring ==================
    def toggle_monitoring(self):
        if not self.monitoring:
            self.monitoring = True
            self.monitor_btn.configure(text="Stop Monitoring")
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
        else:
            self.monitoring = False
            self.monitor_btn.configure(text="Start Monitoring")
            self.log_message("Monitoring stopped.")

    def monitor_loop(self):
        """Background loop that performs ping and TCP checks."""
        interval = self.interval_var.get()
        while self.monitoring:
            for dev in self.devices:
                if not self.monitoring:
                    break
                host = dev["host"]
                port = dev.get("port")
                name = dev["name"]
                timestamp = datetime.now().strftime("%H:%M:%S")

                # Ping
                rtt, ok = ping_host(host)
                ping_status = f"✓ {rtt:.1f} ms" if ok else "✗ timeout"

                # TCP check (only if port is defined)
                tcp_status = ""
                if port:
                    tcp_ok, msg = tcp_check(host, port)
                    tcp_status = f" (TCP port {port}: {'✓ open' if tcp_ok else '✗ closed'})"
                else:
                    tcp_status = " (TCP: n/a)"

                # Log line
                log_line = f"[{timestamp}] {name} ({host}) - Ping: {ping_status}{tcp_status}\n"
                # Schedule UI update
                self.after(0, self.log_message, log_line)
            # Wait interval
            time.sleep(interval)

    def log_message(self, msg):
        """Append a message to the monitoring log."""
        self.mon_log.insert("end", msg)
        self.mon_log.see("end")

    # ================== Diagnostic ==================
    def run_diagnostic(self):
        """Perform a one-time diagnostic on the selected device and update its quality."""
        selected = self.diag_device_var.get()
        if not selected:
            return
        # Find device by the displayed string
        dev_index = None
        dev = None
        for i, d in enumerate(self.devices):
            display = f"{d['name']} ({d['host']})"
            if display == selected:
                dev = d
                dev_index = i
                break
        if dev is None:
            return

        host = dev["host"]
        port = dev.get("port")
        name = dev["name"]

        self.diag_output.delete("1.0", "end")
        self.diag_output.insert("end", f"==== Diagnostic for {name} ({host}) ====\n\n")

        # Ping test (3 packets)
        self.diag_output.insert("end", "--- Ping Test ---\n")
        losses = 0
        rtts = []
        for i in range(3):
            rtt, ok = ping_host(host, timeout=3)
            if ok:
                rtts.append(rtt)
                self.diag_output.insert("end", f"Reply from {host}: time={rtt:.1f}ms\n")
            else:
                losses += 1
                self.diag_output.insert("end", f"Request timeout for {host}\n")
            self.update()
            time.sleep(1)

        # Evaluate quality
        quality_text, quality_tag = evaluate_quality(rtts, losses, 3)

        # Update device quality in memory and treeview
        dev["quality"] = quality_text
        # Refresh the treeview to show the new quality (preserving other columns)
        self.refresh_device_list()

        # Display ping statistics
        if rtts:
            avg = sum(rtts) / len(rtts)
            self.diag_output.insert("end", f"\nPing statistics: packets sent=3, received={len(rtts)}, loss={losses/3*100:.0f}%\n")
            self.diag_output.insert("end", f"Approximate round trip times: min={min(rtts):.1f}ms, max={max(rtts):.1f}ms, avg={avg:.1f}ms\n")
            self.diag_output.insert("end", f"\nQuality: {quality_text}\n")
        else:
            self.diag_output.insert("end", "No successful ping replies.\n")
            self.diag_output.insert("end", f"\nQuality: {quality_text}\n")

        # TCP port check
        if port:
            self.diag_output.insert("end", "\n--- TCP Port Check ---\n")
            ok, msg = tcp_check(host, port)
            if ok:
                self.diag_output.insert("end", f"Port {port} is OPEN (reachable).\n")
            else:
                self.diag_output.insert("end", f"Port {port} is CLOSED or unreachable: {msg}\n")
        else:
            self.diag_output.insert("end", "\n--- TCP Port Check ---\nNo port configured for this device.\n")

        # Traceroute
        self.diag_output.insert("end", "\n--- Traceroute ---\n")
        trace = traceroute(host)
        self.diag_output.insert("end", trace + "\n")

        self.diag_output.insert("end", "\nDiagnostic completed.\n")

# ======================== Run Application ========================
if __name__ == "__main__":
    app = NetworkMonitorApp()
    app.mainloop()