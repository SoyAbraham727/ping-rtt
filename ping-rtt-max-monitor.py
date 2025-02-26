import jcs
import psutil
import csv
import time
import os
import threading
import queue
import argparse
from jnpr.junos import Device

# Configuración de argumentos
parser = argparse.ArgumentParser(description="Monitoreo de sistema y ping a hosts.")
parser.add_argument("--count", type=int, default=1, help="Número de pings por host.")
parser.add_argument("--max-time", type=int, default=60, help="Tiempo máximo de monitoreo en segundos.")
args = parser.parse_args()

COUNT = args.count
MAX_MONITOR_TIME = args.max_time
LOG_INTERVAL = 1
csv_filename = "/var/db/scripts/op/system_monitor.csv"

# Lista de hosts
HOSTS_LIST = ["204.124.107.82", "204.124.107.83", "204.124.107.84"]

data_queue = queue.Queue()
monitoring_done = threading.Event()

# Crear archivo CSV si no existe
if not os.path.exists(csv_filename):
    with open(csv_filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "CPU (%)", "Memoria (%)", "Disco (%)", "Host", "Ping"])

def get_system_usage():
    """Obtiene métricas del sistema (CPU, Memoria y Disco)."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    cpu_percent = round(psutil.cpu_percent(interval=1), 2)
    
    mem = psutil.virtual_memory()
    mem_percent = round((mem.used / (mem.used + mem.available)) * 100, 2)  # Cálculo correcto de memoria

    disk = psutil.disk_usage('/')
    disk_percent = round(disk.percent, 2)
    
    return timestamp, cpu_percent, mem_percent, disk_percent

def log_system_usage():
    """Registra el uso del sistema y lo guarda en la cola."""
    start_time = time.time()
    jcs.syslog("external.warning", "[MONITOREO] Iniciando monitoreo...")

    while not monitoring_done.is_set():
        timestamp, cpu_percent, mem_percent, disk_percent = get_system_usage()
        jcs.syslog("external.warning", f"[{timestamp}] CPU: {cpu_percent}%, Memoria: {mem_percent}%, Disco: {disk_percent}%")

        for host in HOSTS_LIST:
            data_queue.put((timestamp, cpu_percent, mem_percent, disk_percent, host, "N/A"))

        if time.time() - start_time >= MAX_MONITOR_TIME:
            jcs.syslog("external.warning", "[MONITOREO] Tiempo máximo alcanzado, deteniendo monitoreo.")
            monitoring_done.set()
            break

        time.sleep(LOG_INTERVAL)

def ping_host(dev, host):
    """Realiza un ping a un host y guarda el resultado."""
    try:
        result = dev.rpc.ping(host=host, count=str(COUNT))
        target_host = result.findtext("target-host", host).strip()
        jcs.syslog("external.warning", f"Ping exitoso a {target_host}")
        return "Éxito"
    except Exception as e:
        jcs.syslog("external.crit", f"Error en ping a {host}: {e}")
        return "Fallo"

def write_to_csv():
    """Escribe los datos en el archivo CSV en tiempo real."""
    jcs.syslog("external.warning", "[MONITOREO] Iniciando escritura en CSV...")

    while not monitoring_done.is_set() or not data_queue.empty():
        while not data_queue.empty():
            try:
                with open(csv_filename, mode="a", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(data_queue.get())
            except Exception as e:
                jcs.syslog("external.error", f"Error al escribir en CSV: {str(e)}")
        time.sleep(1)

    jcs.syslog("external.warning", "[MONITOREO] Escritura en CSV finalizada.")

def main():
    """Inicia monitoreo y ejecuta ping a cada host en `HOSTS_LIST`."""
    jcs.syslog("external.warning", f"[MONITOREO] Iniciando con COUNT={COUNT}, MAX_TIME={MAX_MONITOR_TIME}s")

    start_time = time.time()
    thread_sys = threading.Thread(target=log_system_usage)
    thread_csv = threading.Thread(target=write_to_csv)

    thread_sys.start()
    thread_csv.start()

    try:
        dev = Device()
        dev.open()

        for host in HOSTS_LIST:
            ping_result = ping_host(dev, host)
            timestamp, cpu_percent, mem_percent, disk_percent = get_system_usage()
            data_queue.put((timestamp, cpu_percent, mem_percent, disk_percent, host, ping_result))

        dev.close()
    except Exception as e:
        jcs.syslog("external.crit", f"Error al conectar con JUNOS: {str(e)}")

    # Finaliza monitoreo cuando terminan los pings
    monitoring_done.set()
    
    thread_sys.join()
    thread_csv.join()

    total_time = round(time.time() - start_time, 3)
    jcs.syslog("external.warning", f"[FINALIZACION] Monitorización completa en {total_time} segundos.")

if __name__ == "__main__":
    main()
