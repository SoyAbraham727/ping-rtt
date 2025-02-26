import argparse
import jcs
import psutil
import csv
import time
import os
import threading
import queue
import sys
import subprocess

# Argumentos desde CLI
parser = argparse.ArgumentParser(description="Monitoreo de sistema en JUNOS")
parser.add_argument("--count", type=int, default=1, help="Numero de iteraciones")
parser.add_argument("--max_time", type=int, default=60, help="Tiempo maximo de monitoreo en segundos")
args = parser.parse_args()

# Configuracion
LOG_INTERVAL = 1
COUNT = args.count
MAX_MONITOR_TIME = args.max_time
csv_filename = "/var/db/scripts/op/system_monitor.csv"

data_queue = queue.Queue()
monitoring_done = threading.Event()

# Verificar existencia del archivo CSV
if not os.path.exists(csv_filename):
    with open(csv_filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "CPU (%)", "Memoria (%)", "Memoria Usada (MB)", "Memoria Libre (MB)", "Disco (%)", "Disco Libre (GB)"])

def convert_bytes(value, unit):
    """Convierte bytes a MB o GB."""
    factor = 1024 ** 2 if unit == "MB" else 1024 ** 3
    return round(value / factor, 3)

def log_system_usage():
    """Registra CPU, memoria y disco en JUNOS."""
    start_time = time.time()
    jcs.syslog("external.warning", "[MONITOREO] Iniciando monitoreo...")

    while not monitoring_done.is_set():
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cpu_percent = round(psutil.cpu_percent(interval=1), 3)

        mem = psutil.virtual_memory()
        memoria_usada = convert_bytes(mem.used, "MB")
        memoria_libre = convert_bytes(mem.available, "MB")
        memoria_porcentaje = round((mem.used / mem.total) * 100, 3)

        disk = psutil.disk_usage('/')
        disk_percent = round(disk.percent, 3)
        disk_free_gb = convert_bytes(disk.free, "GB")

        log_msg = (f"[{timestamp}] CPU: {cpu_percent}%, Memoria: {memoria_porcentaje}% ({memoria_usada} MB usados, {memoria_libre} MB libres), "
                   f"Disco: {disk_percent}% usado ({disk_free_gb} GB libres)")
        
        try:
            jcs.syslog("external.warning", log_msg)
        except Exception as e:
            jcs.syslog("external.error", f"Error en syslog: {str(e)}")

        data_queue.put([timestamp, cpu_percent, memoria_porcentaje, memoria_usada, memoria_libre, disk_percent, disk_free_gb])

        if time.time() - start_time >= MAX_MONITOR_TIME:
            jcs.syslog("external.warning", "[MONITOREO] Tiempo maximo alcanzado, deteniendo monitoreo.")
            monitoring_done.set()
            break

        time.sleep(LOG_INTERVAL)

def write_to_csv():
    """Escribe los datos en el archivo CSV."""
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

def test_subprocess():
    """Ejecuta un comando y captura errores."""
    try:
        result = subprocess.run(["ls", "-l", "/var/db/scripts/op/"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        jcs.syslog("external.warning", f"Salida de ls: {result.stdout.strip()}")
        if result.stderr:
            jcs.syslog("external.error", f"Error en ls: {result.stderr.strip()}")
    except Exception as e:
        jcs.syslog("external.error", f"Fallo en subprocess: {str(e)}")

def main():
    """Inicia el monitoreo."""
    jcs.syslog("external.warning", "[MONITOREO] Iniciando sistema...")

    start_time = time.time()

    thread_sys = threading.Thread(target=log_system_usage)
    thread_csv = threading.Thread(target=write_to_csv)

    thread_sys.start()
    thread_csv.start()

    thread_sys.join()
    monitoring_done.set()
    thread_csv.join()

    total_time = round(time.time() - start_time, 3)
    jcs.syslog("external.warning", f"[FINALIZACION] Monitorizacion completa en {total_time} segundos.")

if __name__ == "__main__":
    test_subprocess()  # Prueba ejecución de comandos
    main()
