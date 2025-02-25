import jcs
import psutil
import csv
import time
import os
from jnpr.junos import Device
from junos import Junos_Context

# Lista de hosts (ejemplo)
HOSTS_LIST = [
    "204.124.107.82", "204.124.107.83", "204.124.107.84",
] * 10  # Repetición de ejemplo

COUNT = 5  # Número de pings por host

# Nombre del archivo CSV donde se guardarán los resultados
csv_filename = "/var/db/scripts/op/ping_results.csv"

# Si el archivo no existe, crear con los encabezados
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Host", "CPU (%)", "Memoria (%)", "Memoria Usada (MB)", "Memoria Libre (MB)", "Disco (%)", "Disco Libre (GB)", "Hora"])

def convert_bytes(value, unit):
    """Convierte bytes a la unidad especificada (MB o GB)."""
    if unit == "MB":
        return round(value / (1024 * 1024), 2)
    elif unit == "GB":
        return round(value / (1024 * 1024 * 1024), 2)
    return round(value, 2)

def log_system_usage():
    """Registra el uso de CPU, memoria y disco en syslog y devuelve los valores corregidos."""
    cpu_percent = round(psutil.cpu_percent(interval=1), 2)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    mem_used_percent = round((mem.used / mem.total) * 100, 2) if mem.total > 0 else 0.00
    mem_used_mb = convert_bytes(mem.used, "MB")
    mem_free_mb = convert_bytes(mem.free, "MB")
    disk_percent = round(disk.percent, 2)
    disk_free_gb = convert_bytes(disk.free, "GB")

    message = f"CPU: {cpu_percent:.2f}%, Memoria: {mem_used_percent:.2f}% ({mem_used_mb:.2f} MB usados, {mem_free_mb:.2f} MB libres), Disco: {disk_percent:.2f}% ({disk_free_gb:.2f} GB libres)"
    jcs.syslog("external.error", f"Uso del sistema - {message}")

    return cpu_percent, mem_used_percent, mem_used_mb, mem_free_mb, disk_percent, disk_free_gb

def ping_host(dev, host):
    """Realiza un ping a un host con una conexión reutilizada y guarda los resultados en el CSV."""
    jcs.syslog("external.error", f"Iniciando ping a {host}")
    cpu_percent, mem_percent, mem_used_mb, mem_free_mb, disk_percent, disk_free_gb = log_system_usage()

    try:
        result = dev.rpc.ping(host=host, count=str(COUNT))
        target_host = result.findtext("target-host", host).strip()
        message = f"Ping ejecutado para {target_host} a las {time.strftime('%Y-%m-%d %H:%M:%S')}"
        jcs.syslog("external.error", f"Ping exitoso a {target_host}")
    except Exception as e:
        message = f"Ping a {host} falló en {time.strftime('%Y-%m-%d %H:%M:%S')}. Error: {e}"
        jcs.syslog("external.crit", f"Error en ping a {host}: {e}")
    
    jcs.syslog("external.crit", message)

    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([host, f"{cpu_percent:.2f}", f"{mem_percent:.2f}", f"{mem_used_mb:.2f}", f"{mem_free_mb:.2f}", f"{disk_percent:.2f}", f"{disk_free_gb:.2f}", time.strftime("%Y-%m-%d %H:%M:%S")])

def main():
    """Ejecuta el proceso para cada host y guarda los resultados en CSV."""
    jcs.syslog("external.error", "Iniciando conexión con el dispositivo Juniper")
    
    with Device() as dev:
        initial_cpu, initial_mem, initial_mem_used_mb, initial_mem_free_mb, initial_disk, initial_disk_free_gb = log_system_usage()
        
        with open(csv_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Estado Inicial", f"{initial_cpu:.2f}", f"{initial_mem:.2f}", f"{initial_mem_used_mb:.2f}", f"{initial_mem_free_mb:.2f}", f"{initial_disk:.2f}", f"{initial_disk_free_gb:.2f}", time.strftime("%Y-%m-%d %H:%M:%S")])

        for host in HOSTS_LIST:
            jcs.syslog("external.error", f"Procesando host: {host}")
            ping_host(dev, host)
    
    jcs.syslog("external.error", "Ejecución del script finalizada")
    log_system_usage()

if __name__ == "__main__":
    main()
