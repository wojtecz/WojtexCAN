import serial
import serial.tools.list_ports
import threading
import tkinter as tk
from tkinter import ttk
import time

ser = None
all_frames = []

root = tk.Tk()
root.title("CAN MCP2515")

stop_log = tk.BooleanVar(value=False, master=root)

can_speed_dict = {
    "5 kbps": "01", "10 kbps": "02", "20 kbps": "03", "31.25 kbps": "04",
    "33 kbps": "05", "40 kbps": "06", "50 kbps": "07", "80 kbps": "08",
    "83.3 kbps": "09", "95 kbps": "10", "100 kbps": "11", "125 kbps": "12",
    "200 kbps": "13", "250 kbps": "14", "500 kbps": "15", "1000 kbps": "16",
}

# ---------- SERIAL ----------
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
        ser = None
        status_label.config(text="Disconnected")

# ---------- FRAMES ----------
def record_frame(frame):
    if stop_log.get():
        return
    tree.insert('', 'end',
        values=[frame["ID"], frame["DLC"], *frame["DATA"], frame["DIR"]],
        tags=(frame["DIR"].lower(),))
    tree.yview_moveto(1)

def send_frame():
    if not ser or not ser.is_open:
        return
    can_id = id_entry.get().zfill(4)
    speed_num = can_speed_dict.get(speed_var.get(), "11")
    dlc = int(dlc_spinbox.get())
    data = [int(sb.get()) for sb in data_spinboxes]
    data_str = ''.join(f"{b:03d}" for b in data)
    ser.write(f"1{speed_num}{can_id}{data_str}A".encode())
    record_frame({"ID": can_id, "DLC": dlc, "DATA": data, "DIR": "TX"})

# ---------- SERIAL READ ----------
def read_serial():
    while True:
        try:
            if ser and ser.is_open and ser.in_waiting:
                line = ser.readline().decode(errors="ignore").strip()
                if line.startswith("R;"):
                    p = line.split(";")
                    data = [int(x) for x in p[3:11]]
                    record_frame({
                        "ID": p[1], "DLC": int(p[2]),
                        "DATA": data, "DIR": "RX"
                    })
        except:
            pass
        time.sleep(0.001)

# ---------- BIT HANDLING ----------
def update_bits_from_byte(byte):
    val = int(data_spinboxes[byte].get())
    for b in range(8):
        bit_vars[byte][b].set((val >> b) & 1)

def update_byte_from_bits(byte):
    val = 0
    for b in range(8):
        if bit_vars[byte][b].get():
            val |= (1 << b)
    sb = data_spinboxes[byte]
    sb.delete(0, "end")
    sb.insert(0, str(val))

# ---------- GUI ----------
# COM
ttk.Label(root, text="COM").grid(row=0, column=0)
port_var = tk.StringVar()
port_box = ttk.Combobox(root, textvariable=port_var, width=8)
port_box.grid(row=0, column=1)
port_box['values'] = [p.device for p in serial.tools.list_ports.comports()]
if port_box['values']:
    port_box.current(0)

# Speed
ttk.Label(root, text="Speed").grid(row=0, column=2)
speed_var = tk.StringVar(value="100 kbps")
ttk.Combobox(root, textvariable=speed_var,
             values=list(can_speed_dict.keys()), width=10)\
    .grid(row=0, column=3)

# ID / DLC
ttk.Label(root, text="ID").grid(row=1, column=0)
id_entry = ttk.Entry(root, width=6)
id_entry.insert(0, "0207")
id_entry.grid(row=1, column=1)

ttk.Label(root, text="DLC").grid(row=1, column=2)
dlc_spinbox = tk.Spinbox(root, from_=0, to=8, width=4)
dlc_spinbox.insert(0, "8")
dlc_spinbox.grid(row=1, column=3)
dlc_spinbox.delete(0, "end")
dlc_spinbox.insert(0, "8")
# DATA + BITS
data_spinboxes = []
bit_vars = []

for i in range(8):
    ttk.Label(root, text=f"D{i}").grid(row=2, column=i)
    sb = tk.Spinbox(root, from_=0, to=255, width=4,
                    command=lambda i=i: update_bits_from_byte(i))
    sb.insert(0, "0")
    sb.grid(row=3, column=i)
    sb.bind("<KeyRelease>", lambda e, i=i: update_bits_from_byte(i))
    data_spinboxes.append(sb)

    bits = []
    for b in range(8):
        v = tk.IntVar()
        ttk.Checkbutton(
            root, text=f"b{b}", variable=v,
            command=lambda i=i: update_byte_from_bits(i)
        ).grid(row=4+b, column=i, sticky="w")
        bits.append(v)
    bit_vars.append(bits)

# Buttons
ttk.Button(root, text="Connect", command=connect).grid(row=12, column=0)
ttk.Button(root, text="Disconnect", command=disconnect).grid(row=12, column=1)
ttk.Button(root, text="Send", command=send_frame).grid(row=12, column=2)

# Table
cols = ["ID","DLC","D0","D1","D2","D3","D4","D5","D6","D7","DIR"]
tree = ttk.Treeview(root, columns=cols, show="headings", height=8)
for c in cols:
    tree.heading(c, text=c)
    tree.column(c, width=50)
tree.grid(row=13, column=0, columnspan=8)
tree.tag_configure("tx", foreground="green")
tree.tag_configure("rx", foreground="blue")

status_label = ttk.Label(root, text="Not connected")
status_label.grid(row=14, column=0, columnspan=8, sticky="w")

threading.Thread(target=read_serial, daemon=True).start()
root.mainloop()
