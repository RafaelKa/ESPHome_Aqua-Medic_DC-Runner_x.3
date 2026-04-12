import serial
import time
import threading
import queue
import os

# Konfiguration
PORT_ESP_TO_MCU = '/dev/serial/by-id/usb-Duppa_srl_USB_QUADPORT_VE.DIRECT_Du2A9QsYYk-if01-port0'
PORT_MCU_TO_ESP = '/dev/serial/by-id/usb-Duppa_srl_USB_QUADPORT_VE.DIRECT_Du2A9QsYYk-if00-port0'
BAUD = 9600

# Dateiname mit Zeitstempel generieren
file_timestamp = time.strftime("%Y.%m.%d_%H.%M.%S")
LOG_FILE = f"Sniffing.{file_timestamp}-log.yaml"

data_queue = queue.Queue()

def get_timestamp():
    t = time.time()
    return time.strftime("%Y.%m.%d --- %H:%M:%S", time.localtime(t)) + f":{int(t*1000)%1000:03d}"

def reader_thread(port, label):
    """Liest Bytes ohne Verzögerung."""
    try:
        ser = serial.Serial(port, BAUD, timeout=0.1)
        while True:
            byte = ser.read(1)
            if byte:
                data_queue.put((time.time(), label, byte.hex()))
    except Exception as e:
        print(f"\n[!] Fehler an {port} ({label}): {e}")

def writer_worker():
    """Schreibt valides YAML Format."""
    buffers = {"ESP": [], "MCU": []}
    
    with open(LOG_FILE, "a") as f:
        while True:
            t_event, label, hex_val = data_queue.get()
            
            # Paket-Ende Erkennung bei neuem f5 Header
            if hex_val == "f5" and buffers[label]:
                ts = time.strftime("%Y.%m.%d --- %H:%M:%S", time.localtime(t_event)) + f":{int(t_event*1000)%1000:03d}"
                packet = " ".join(buffers[label])
                
                # Valide YAML Listen-Struktur
                f.write(f"  -\n")
                f.write(f"    timestamp_{label}: '{ts}'\n")
                f.write(f"    {label}_Data: '0x{packet}'\n")
                f.flush()
                
                buffers[label] = []
            
            buffers[label].append(hex_val)
            data_queue.task_done()

# Datei initialisieren
with open(LOG_FILE, "w") as f:
    f.write(f"# Sniffing started: {get_timestamp()}\n")
    f.write("logging:\n")

# Threads starten
threading.Thread(target=reader_thread, args=(PORT_ESP_TO_MCU, "ESP"), daemon=True).start()
threading.Thread(target=reader_thread, args=(PORT_MCU_TO_ESP, "MCU"), daemon=True).start()
threading.Thread(target=writer_worker, daemon=True).start()

print(f"--- Sniffer läuft (SILENT MODE) ---")
print(f"Datei: {LOG_FILE}")
print(f"Tippe deine Kommentare einfach hier ein und drücke ENTER.")
print(f"Beenden mit STRG+C")

try:
    while True:
        comment = input("") # Hier kannst du tippen, ohne dass Text dazwischenfunkt
        if comment:
            with open(LOG_FILE, "a") as f:
                ts_comment = time.strftime("%H:%M:%S") + f":{int(time.time()*1000)%1000:03d}"
                f.write(f"# {ts_comment} --- {comment}\n")
            print(f"[Log] Kommentar gespeichert.")
except KeyboardInterrupt:
    print(f"\nFertig. Logdatei: {LOG_FILE}")
