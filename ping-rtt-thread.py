import jcs
import psutil
import csv
import time
import os
import threading
import queue
from jnpr.junos import Device

# Configuración
LOG_INTERVAL = 5  # Intervalo de registro en segundos
COUNT = 1  # Número de pings por host
HOSTS_LIST = ["204.124.107.82"]  # Lista de hosts a monitorear
csv_filename = "/var/db/scripts/op/system_monitor.csv"

# Cola para almacenar los datos antes de escribir en CSV
data_queue = queue.Queue()

# Si el archivo no existe, crear con los encabezados
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "CPU (%)", "Memoria (%)", "Memoria Usada (MB)", "Memoria Libre (MB)", "Disco (%)", "Disco Libre (GB)", "Host", "RTT Min (ms)", "RTT Max (ms)", "RTT Prom (ms)"])

def convert_bytes(value, unit):
    """Convierte bytes a la unidad especificada (MB o GB)."""
    factor = 1024 * 1024 if unit == "MB" else 1024 * 1024 * 1024
    return round(value / factor, 2)

def log_system_usage():
    """Registra el uso de CPU, memoria y disco y lo almacena en la cola."""
    while True:
        cpu_percent = round(psutil.cpu_percent(interval=1), 2)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        mem_used_percent = round(mem.percent, 2)
        mem_used_mb = convert_bytes(mem.used, "MB")
        mem_free_mb = convert_bytes(mem.free, "MB")
        disk_percent = round(disk.percent, 2)
        disk_free_gb = convert_bytes(disk.free, "GB")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        data_queue.put([timestamp, cpu_percent, mem_used_percent, mem_used_mb, mem_free_mb, disk_percent, disk_free_gb, None, None, None, None])
        time.sleep(LOG_INTERVAL)

def ping_hosts():
    """Realiza pings a los hosts y almacena los resultados en la cola."""
    while True:
        for host in HOSTS_LIST:
            try:
                with Device() as dev:
                    result = dev.rpc.ping(host=host, count=str(COUNT))
                    rtt_min = round(float(result.findtext("probe-results-summary/rtt-minimum", "0.0")), 2)
                    rtt_max = round(float(result.findtext("probe-results-summary/rtt-maximum", "0.0")), 2)
                    rtt_avg = round(float(result.findtext("probe-results-summary/rtt-average", "0.0")), 2)
            except Exception:
                rtt_min, rtt_max, rtt_avg = 0.00, 0.00, 0.00
            
            data_queue.put([time.strftime("%Y-%m-%d %H:%M:%S"), None, None, None, None, None, None, host, rtt_min, rtt_max, rtt_avg])
        
        time.sleep(LOG_INTERVAL)

def write_to_csv():
    """Escribe los datos almacenados en la cola al archivo CSV."""
    while True:
        while not data_queue.empty():
            with open(csv_filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(data_queue.get())
        time.sleep(1)

def main():
    """Inicia los hilos para la monitorización y escritura en CSV."""
    jcs.syslog("external.error", "Iniciando monitorización del sistema con ping en paralelo")
    
    thread_sys = threading.Thread(target=log_system_usage, daemon=True)
    thread_ping = threading.Thread(target=ping_hosts, daemon=True)
    thread_csv = threading.Thread(target=write_to_csv, daemon=True)
    
    thread_sys.start()
    thread_ping.start()
    thread_csv.start()
    
    thread_sys.join()
    thread_ping.join()
    thread_csv.join()
    
    jcs.syslog("external.error", "Monitorización finalizada")

if __name__ == "__main__":
    main()
