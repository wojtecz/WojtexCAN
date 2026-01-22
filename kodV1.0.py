import serial
import serial.tools.list_ports
import threading
import tkinter as tk
from tkinter import ttk
import time

ser = None
stop_log = None
auto_id = None
auto_id_thread = None
auto_id_running = False
all_frames = []  # lista wszystkich ramek dla filtrowania

# --- GUI ---
root = tk.Tk()
root.title("CAN MCP2515")

stop_log = tk.BooleanVar(value=False, master=root)
auto_id = tk.BooleanVar(value=False, master=root)

# --- CAN Speed mapping ---
can_speed_dict = {
    "5 kbps": "01", "10 kbps": "02", "20 kbps": "03", "31.25 kbps": "04",
    "33 kbps": "05", "40 kbps": "06", "50 kbps": "07", "80 kbps": "08",
    "83.3 kbps": "09", "95 kbps": "10", "100 kbps": "11", "125 kbps": "12",
    "200 kbps": "13", "250 kbps": "14", "500 kbps": "15", "1000 kbps": "16",
}

# --- Functions ---
def connect():
    global ser
    try:
        ser = serial.Serial(port_var.get(), 115200, timeout=0.1)
        status_label.config(text=f"Connected to {port_var.get()}")
    except Exception as e:
        status_label.config(text=f"Connection error: {e}")

def disconnect():
    global ser
    if ser and ser.is_open:
        ser.close()
        status_label.config(text="Disconnected")
        ser = None

def apply_filters():
    """Display only frames that match the filter"""
    tree.delete(*tree.get_children())
    id_filter_val = filter_id_entry.get().strip()
    dir_filter_val = dir_filter_var.get()
    
    for frame in all_frames:
        frame_id = frame["ID"]
        frame_dir = frame["DIR"]
        # Filter ID
        if id_filter_val and frame_id != id_filter_val:
            continue
        # Filter TX/RX
        if dir_filter_val != "ALL" and frame_dir != dir_filter_val:
            continue
        tree.insert('', 'end', values=[frame["ID"], frame["DLC"], *frame["DATA"], frame["DIR"]],
                    tags=(frame_dir.lower(),))

def record_frame(frame):
    """Add frame to list and display if it passes filters"""
    all_frames.append(frame)
    if not stop_log.get():
        frame_id = frame["ID"]
        frame_dir = frame["DIR"]
        id_filter_val = filter_id_entry.get().strip()
        dir_filter_val = dir_filter_var.get()
        if id_filter_val and frame_id != id_filter_val:
            return
        if dir_filter_val != "ALL" and frame_dir != dir_filter_val:
            return
        tree.insert('', 'end', values=[frame["ID"], frame["DLC"], *frame["DATA"], frame["DIR"]],
                    tags=(frame_dir.lower(),))
        tree.yview_moveto(1)

def send_frame(can_id_override=None):
    if not ser or not ser.is_open:
        status_label.config(text="Port not connected")
        return
    try:
        can_id = id_entry.get().zfill(4) if can_id_override is None else str(can_id_override).zfill(4)
        speed_num = can_speed_dict.get(speed_var.get(), "11")
        dlc = int(dlc_spinbox.get())
        data_bytes = [int(sb.get()) for sb in data_spinboxes[:dlc]]
        full_data_bytes = data_bytes + [0]*(8 - dlc)
        data_str = ''.join(f"{b:03d}" for b in full_data_bytes)
        frame_str = f"1{speed_num}{can_id}{data_str}A"
        ser.write(frame_str.encode())
        record_frame({"ID": can_id, "DLC": dlc, "DATA": full_data_bytes, "DIR": "TX"})
    except Exception as e:
        status_label.config(text=f"Send error: {e}")

def clear_table():
    all_frames.clear()
    tree.delete(*tree.get_children())

def read_serial():
    while True:
        try:
            if ser and ser.is_open:
                if ser.in_waiting:
                    line = ser.readline().decode(errors="ignore").strip()
                    if line and line.startswith("R;"):
                        parts = line.split(';')
                        can_id = parts[1]
                        dlc = int(parts[2])
                        data_bytes = [int(x) for x in parts[3:3+dlc]]
                        full_data_bytes = data_bytes + [0]*(8-dlc)
                        record_frame({"ID": can_id, "DLC": dlc, "DATA": full_data_bytes, "DIR": "RX"})
        except serial.SerialException:
            # jeśli port został zamknięty w trakcie odczytu
            time.sleep(0.1)
        except Exception:
            pass
        time.sleep(0.001)

def refresh_ports():
    ports = [p.device for p in serial.tools.list_ports.comports()]
    port_box['values'] = ports
    if ports:
        port_box.current(0)

def auto_id_loop():
    global auto_id_running
    start = int(start_id_entry.get())
    end = int(end_id_entry.get())
    delay_ms = int(delay_entry.get())
    auto_id_running = True
    current = start
    while auto_id.get() and auto_id_running:
        send_frame(can_id_override=current)
        current += 1
        if current > end:
            current = start
        time.sleep(delay_ms/1000)

def toggle_auto_id():
    global auto_id_thread, auto_id_running
    if auto_id.get():
        auto_id_thread = threading.Thread(target=auto_id_loop, daemon=True)
        auto_id_thread.start()
    else:
        auto_id_running = False

# --- GUI ELEMENTS ---

padx_small = 5
pady_small = 5

# Port COM
ttk.Label(root, text="COM Port").grid(row=0, column=0, padx=padx_small, pady=pady_small)
port_var = tk.StringVar()
port_box = ttk.Combobox(root, textvariable=port_var, width=10)
port_box.grid(row=0, column=1, padx=padx_small, pady=pady_small)
refresh_ports()

# CAN Speed
ttk.Label(root, text="CAN Speed").grid(row=0, column=2, padx=padx_small, pady=pady_small)
speed_var = tk.StringVar(value="100 kbps")
speed_box = ttk.Combobox(root, textvariable=speed_var, width=10,
                         values=list(can_speed_dict.keys()))
speed_box.grid(row=0, column=3, padx=padx_small, pady=pady_small)

# CAN ID and DLC
ttk.Label(root, text="CAN ID").grid(row=1, column=0, padx=padx_small, pady=pady_small)
id_entry = ttk.Entry(root, width=6)
id_entry.grid(row=1, column=1, padx=padx_small, pady=pady_small)
id_entry.insert(0, "0207")

ttk.Label(root, text="DLC").grid(row=1, column=2, padx=padx_small, pady=pady_small)
dlc_spinbox = tk.Spinbox(root, from_=0, to=8, width=4)
dlc_spinbox.grid(row=1, column=3, padx=padx_small, pady=pady_small)
dlc_spinbox.delete(0,"end")
dlc_spinbox.insert(0,"8")

# Data D0-D7 with labels
data_spinboxes = []
for i in range(8):
    ttk.Label(root, text=f"D{i}").grid(row=2, column=i*2, padx=padx_small, pady=pady_small)
    sb = tk.Spinbox(root, from_=0, to=255, width=4)
    sb.grid(row=2, column=i*2+1, padx=padx_small, pady=pady_small)
    sb.delete(0,"end")
    sb.insert(0,"0")
    data_spinboxes.append(sb)

# Auto-ID
ttk.Label(root, text="Start ID").grid(row=1, column=16, padx=padx_small, pady=pady_small)
start_id_entry = ttk.Entry(root, width=6)
start_id_entry.grid(row=1, column=17, padx=padx_small, pady=pady_small)
start_id_entry.insert(0, "0")

ttk.Label(root, text="End ID").grid(row=1, column=18, padx=padx_small, pady=pady_small)
end_id_entry = ttk.Entry(root, width=6)
end_id_entry.grid(row=1, column=19, padx=padx_small, pady=pady_small)
end_id_entry.insert(0, "2047")

ttk.Label(root, text="Delay ms").grid(row=1, column=20, padx=padx_small, pady=pady_small)
delay_entry = ttk.Entry(root, width=6)
delay_entry.grid(row=1, column=21, padx=padx_small, pady=pady_small)
delay_entry.insert(0, "50")

# Connect, Disconnect, Send, Clear
ttk.Button(root, text="Connect", command=connect).grid(row=0, column=4, padx=padx_small, pady=pady_small)
ttk.Button(root, text="Disconnect", command=disconnect).grid(row=0, column=5, padx=padx_small, pady=pady_small)
ttk.Button(root, text="Send", command=send_frame).grid(row=3, column=0, padx=padx_small, pady=pady_small)
ttk.Button(root, text="Clear", command=clear_table).grid(row=3, column=1, padx=padx_small, pady=pady_small)

# Stop log
ttk.Checkbutton(root, text="Stop Log", variable=stop_log).grid(row=3, column=2, padx=padx_small, pady=pady_small)
# Auto ID
ttk.Checkbutton(root, text="Auto ID", variable=auto_id, command=toggle_auto_id).grid(row=3, column=3, padx=padx_small, pady=pady_small)

# Filters
ttk.Label(root, text="Filter ID").grid(row=3, column=4, padx=padx_small, pady=pady_small)
filter_id_entry = ttk.Entry(root, width=6)
filter_id_entry.grid(row=3, column=5, padx=padx_small, pady=pady_small)

ttk.Label(root, text="Filter DIR").grid(row=3, column=6, padx=padx_small, pady=pady_small)
dir_filter_var = tk.StringVar(value="ALL")
dir_filter_box = ttk.Combobox(root, textvariable=dir_filter_var, width=6,
                              values=["ALL","TX","RX"])
dir_filter_box.grid(row=3, column=7, padx=padx_small, pady=pady_small)
ttk.Button(root, text="Apply Filters", command=apply_filters).grid(row=3, column=8, padx=padx_small, pady=pady_small)

# Table
columns = ["ID","DLC","D0","D1","D2","D3","D4","D5","D6","D7","DIR"]
tree = ttk.Treeview(root, columns=columns, show="headings", height=15)
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=50)
tree.grid(row=4, column=0, columnspan=22, padx=padx_small, pady=pady_small)
tree.tag_configure("tx", foreground="green")
tree.tag_configure("rx", foreground="blue")

# Status
status_label = ttk.Label(root, text="Not connected")
status_label.grid(row=5, column=0, columnspan=22, sticky="w", padx=padx_small, pady=pady_small)

# Serial read thread
threading.Thread(target=read_serial, daemon=True).start()

root.mainloop()
