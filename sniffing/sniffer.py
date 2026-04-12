import serial
import time
import threading
import queue
import os

# --- Configuration ---
# Update these paths to your specific USB serial ports
PORT_ESP_TO_MCU = '/dev/serial/by-id/usb-Duppa_srl_USB_QUADPORT_VE.DIRECT_Du2A9QsYYk-if01-port0'
PORT_MCU_TO_ESP = '/dev/serial/by-id/usb-Duppa_srl_USB_QUADPORT_VE.DIRECT_Du2A9QsYYk-if00-port0'
BAUD = 9600
TIMEOUT_MS = 0.050  # 50ms silence indicates end of packet

# Generate Log-File with timestamp
file_timestamp = time.strftime("%Y.%m.%d_%H.%M.%S")
LOG_FILE = f"Sniffing.{file_timestamp}-log.yaml"

data_queue = queue.Queue()

def get_timestamp(t=None):
    if t is None:
        t = time.time()
    return time.strftime("%Y.%m.%d --- %H:%M:%S", time.localtime(t)) + f":{int(t*1000)%1000:03d}"

def reader_thread(port, label):
    """Reads bytes from the serial port and puts them into the queue."""
    try:
        ser = serial.Serial(port, BAUD, timeout=0.01)
        while True:
            byte = ser.read(1)
            if byte:
                data_queue.put((time.time(), label, byte.hex()))
    except Exception as e:
        print(f"\n[!] Error on {port} ({label}): {e}")

def write_packet(f, label, data_list, t_start):
    """Helper to write a finished packet to the YAML file."""
    ts = get_timestamp(t_start)
    packet = " ".join(data_list)
    f.write(f"  -\n")
    f.write(f"    timestamp_{label}: '{ts}'\n")
    f.write(f"    {label}_Data: '0x{packet}'\n")
    f.flush()

def writer_worker():
    """Processes bytes from the queue and groups them into packets based on timing."""
    buffers = {"ESP": [], "MCU": []}
    start_times = {"ESP": 0, "MCU": 0}
    last_byte_times = {"ESP": 0, "MCU": 0}

    with open(LOG_FILE, "a") as f:
        while True:
            try:
                # Check for new data with a short timeout
                t_event, label, hex_val = data_queue.get(timeout=0.02)

                # If buffer is empty, this is the start of a new packet
                if not buffers[label]:
                    start_times[label] = t_event

                # If the gap between bytes is too large, write the previous buffer first
                # (Safety check in case the loop was busy)
                if buffers[label] and (t_event - last_byte_times[label] > TIMEOUT_MS):
                    write_packet(f, label, buffers[label], start_times[label])
                    buffers[label] = []
                    start_times[label] = t_event

                buffers[label].append(hex_val)
                last_byte_times[label] = t_event
                data_queue.task_done()

            except queue.Empty:
                # No data in queue? Check if existing buffers need to be flushed due to timeout
                now = time.time()
                for lbl in ["ESP", "MCU"]:
                    if buffers[lbl] and (now - last_byte_times[lbl] > TIMEOUT_MS):
                        write_packet(f, lbl, buffers[lbl], start_times[lbl])
                        buffers[lbl] = []

# Initialize file
with open(LOG_FILE, "w") as f:
    f.write(f"# Sniffing started: {get_timestamp()}\n")
    f.write("logging:\n")

# Start Threads
threading.Thread(target=reader_thread, args=(PORT_ESP_TO_MCU, "ESP"), daemon=True).start()
threading.Thread(target=reader_thread, args=(PORT_MCU_TO_ESP, "MCU"), daemon=True).start()
threading.Thread(target=writer_worker, daemon=True).start()

print(f"--- Sniffer running (TIMING BASED MODE) ---")
print(f"Logging every byte sequence, not just 0xF5 packets.")
print(f"File: {LOG_FILE}")
print(f"Type your comments and press ENTER to bookmark events in the log.")
print(f"Press CTRL+C to stop.")

try:
    while True:
        comment = input("")
        if comment:
            with open(LOG_FILE, "a") as f:
                ts_comment = time.strftime("%H:%M:%S") + f":{int(time.time()*1000)%1000:03d}"
                f.write(f"# {ts_comment} --- {comment}\n")
            print(f"[Log] Comment saved.")
except KeyboardInterrupt:
    print(f"\nFinished. Log file: {LOG_FILE}")
