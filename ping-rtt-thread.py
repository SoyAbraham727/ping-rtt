import jcs
import psutil
import csv
import time
import os
import threading
import queue
from jnpr.junos import Device

# Configuración
LOG_INTERVAL = 1  # Intervalo de registro en segundos
COUNT = 5  # Número de pings por host
HOSTS_LIST = ["204.124.107.82"]  # Lista de hosts a monitorear
csv_filename = "/var/db/scripts/op/system_monitor.csv"
MAX_MONITOR_TIME = 5  # Tiempo máximo de monitoreo en segundos

# Cola para almacenar los datos antes de escribir en CSV
data_queue = queue.Queue()

# Bandera de finalización
monitoring_done = threading.Event()

# Si el archivo no existe, crearlo con encabezados
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "CPU (%)", "Memoria (%)", "Memoria Usada (MB)", "Memoria Libre (MB)", "Disco (%)", "Disco Libre (GB)", "Host", "RTT Min (ms)", "RTT Max (ms)", "RTT Prom (ms)"])

def convert_bytes(value, unit):
    """Convierte bytes a la unidad especificada (MB o GB), evitando valores negativos."""
    value = max(value, 0)  
    factor = 1024 * 1024 if unit == "MB" else 1024 * 1024 * 1024
    return round(value / factor, 2)

def log_system_usage():
    """Registra el uso de CPU, memoria y disco mientras el monitoreo esté activo."""
    jcs.syslog("external.warning", "[MONITOREO] Iniciando monitoreo de recursos del sistema...")
    start_time = time.time()
    
    while not monitoring_done.is_set():
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cpu_percent = round(psutil.cpu_percent(interval=1), 2)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        mem_used_percent = round(mem.percent, 2)
        mem_used_mb = convert_bytes(mem.used, "MB")
        mem_free_mb = convert_bytes(mem.available, "MB")
        disk_percent = round(disk.percent, 2)
        disk_free_gb = convert_bytes(disk.free, "GB")

        log_msg = (f"[{timestamp}] CPU: {cpu_percent}%, Memoria: {mem_used_percent}% ({mem_used_mb} MB usados, {mem_free_mb} MB libres), "
                   f"Disco: {disk_percent}% usado ({disk_free_gb} GB libres)")
        jcs.syslog("external.warning", log_msg)

        data_queue.put([timestamp, cpu_percent, mem_used_percent, mem_used_mb, mem_free_mb, disk_percent, disk_free_gb, None, None, None, None])

        # Salir si se supera el tiempo máximo
        if time.time() - start_time >= MAX_MONITOR_TIME:
            jcs.syslog("external.warning", "[MONITOREO] Tiempo máximo alcanzado, deteniendo monitoreo del sistema.")
            monitoring_done.set()
            break

        time.sleep(LOG_INTERVAL)

def ping_hosts():
    """Realiza pings a los hosts y almacena los resultados en la cola."""
    jcs.syslog("external.warning", "[MONITOREO] Iniciando monitoreo de conectividad de red...")
    for host in HOSTS_LIST:
        try:
            with Device() as dev:
                result = dev.rpc.ping(host=host, count=str(COUNT))
                rtt_min = round(float(result.findtext("probe-results-summary/rtt-minimum", "0.0")), 2)
                rtt_max = round(float(result.findtext("probe-results-summary/rtt-maximum", "0.0")), 2)
                rtt_avg = round(float(result.findtext("probe-results-summary/rtt-average", "0.0")), 2)
                log_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ping a {host}: Min {rtt_min}ms, Max {rtt_max}ms, Prom {rtt_avg}ms"
                jcs.syslog("external.warning", log_msg)
                data_queue.put([time.strftime("%Y-%m-%d %H:%M:%S"), None, None, None, None, None, None, host, rtt_min, rtt_max, rtt_avg])
        except Exception:
            jcs.syslog("external.critical", f"[ERROR] Fallo en ping a {host}")

    jcs.syslog("external.warning", "[MONITOREO] Todos los pings han finalizado. Deteniendo monitoreo del sistema...")
    monitoring_done.set()

def write_to_csv():
    """Escribe los datos almacenados en la cola al archivo CSV mientras haya datos en la cola."""
    jcs.syslog("external.warning", "[MONITOREO] Iniciando escritura de datos en CSV...")
    while not monitoring_done.is_set() or not data_queue.empty():
        while not data_queue.empty():
            with open(csv_filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(data_queue.get())
        time.sleep(1)
    jcs.syslog("external.warning", "[MONITOREO] Escritura en CSV finalizada.")

def main():
    """Inicia los hilos para la monitorización y escritura en CSV."""
    jcs.syslog("external.warning", "[MONITOREO] Iniciando monitoreo del sistema y red...")
    
    thread_sys = threading.Thread(target=log_system_usage)
    thread_ping = threading.Thread(target=ping_hosts)
    thread_csv = threading.Thread(target=write_to_csv)

    thread_sys.start()
    thread_ping.start()
    thread_csv.start()

    thread_ping.join()  # Esperar a que finalicen los pings
    monitoring_done.set()  # Asegurar que el monitoreo del sistema también se detenga
    thread_sys.join()   # Asegurar que el monitoreo del sistema finalice
    thread_csv.join()   # Asegurar que la escritura en CSV termine correctamente

    jcs.syslog("external.warning", "[FINALIZACIÓN] Monitorización completa.")

if __name__ == "__main__":
    main()
